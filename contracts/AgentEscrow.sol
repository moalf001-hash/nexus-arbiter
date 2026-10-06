// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev واجهة ERC-20 القياسية للتعامل مع عملة USDC
 */
interface IERC20 {
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title AgentEscrow - بروتوكول التحكيم والضمان المالي بين وكلاء الذكاء الاصطناعي
 */
contract AgentEscrow {
    // نسبة عمولة المنصة: 150 نقطة أساس = 1.5%
    uint256 public constant PLATFORM_FEE_BPS = 150; 
    uint256 public constant BPS_DENOMINATOR = 10000;

    address public immutable platformOwner; // عنوان محفظتك لتلقي الأرباح
    address public arbiterEngine;           // عنوان محرك التحكيم المخول بالبت النهائي
    IERC20 public immutable usdcToken;      // عقد عملة USDC

    enum EscrowStatus {
        EMPTY,
        LOCKED,
        SETTLED,
        REFUNDED
    }

    struct EscrowDeal {
        bytes32 sessionId;
        address buyer;
        address seller;
        uint256 amount;          // القيمة بوحدات USDC (6 خانات عشرية)
        uint256 deadline;        // التوقيت الحتمي لانتهاء مهلة SLA
        bytes32 agreementHash;   // بصمة العقد المشفر المتفق عليه
        EscrowStatus status;
    }

    // ربط معرف الجلسة ببيانات الصفقة
    mapping(bytes32 => EscrowDeal) public deals;

    event FundsLocked(bytes32 indexed sessionId, address indexed buyer, address indexed seller, uint256 amount, uint256 deadline);
    event FundsSettled(bytes32 indexed sessionId, uint256 sellerAmount, uint256 platformFee);
    event FundsRefunded(bytes32 indexed sessionId, address indexed buyer, uint256 amount);

    modifier onlyArbiterOrBuyer(bytes32 sessionId) {
        require(
            msg.sender == arbiterEngine || msg.sender == deals[sessionId].buyer,
            "Unauthorized: Only buyer or arbiter engine can release funds"
        );
        _;
    }

    modifier onlyPlatformOwner() {
        require(msg.sender == platformOwner, "Unauthorized: Only platform owner");
        _;
    }

    constructor(address _usdcToken, address _arbiterEngine) {
        require(_usdcToken != address(0), "Invalid token address");
        require(_arbiterEngine != address(0), "Invalid arbiter address");
        platformOwner = msg.sender;
        arbiterEngine = _arbiterEngine;
        usdcToken = IERC20(_usdcToken);
    }

    /**
     * @notice حجز أموال الصفقة من حساب المشتري بعد انتهاء التفاوض
     */
    function lockFunds(
        bytes32 sessionId,
        address seller,
        uint256 amount,
        uint256 durationSeconds,
        bytes32 agreementHash
    ) external {
        require(deals[sessionId].status == EscrowStatus.EMPTY, "Deal already exists");
        require(seller != address(0) && seller != msg.sender, "Invalid seller address");
        require(amount > 0, "Amount must be greater than zero");

        deals[sessionId] = EscrowDeal({
            sessionId: sessionId,
            buyer: msg.sender,
            seller: seller,
            amount: amount,
            deadline: block.timestamp + durationSeconds,
            agreementHash: agreementHash,
            status: EscrowStatus.LOCKED
        });

        // سحب USDC من المشتري إلى خزينة العقد الذكي
        require(usdcToken.transferFrom(msg.sender, address(this), amount), "USDC Transfer failed");

        emit FundsLocked(sessionId, msg.sender, seller, amount, block.timestamp + durationSeconds);
    }

    /**
     * @notice تسوية الصفقة: اقتطاع 1.5% لمحفظة المالك وتحويل 98.5% للبائع
     */
    function settleAndSplit(bytes32 sessionId) external onlyArbiterOrBuyer(sessionId) {
        EscrowDeal storage deal = deals[sessionId];
        require(deal.status == EscrowStatus.LOCKED, "Deal is not locked");

        deal.status = EscrowStatus.SETTLED;

        // حساب عمولة المنصة الصافية (1.5%)
        uint256 fee = (deal.amount * PLATFORM_FEE_BPS) / BPS_DENOMINATOR;
        uint256 sellerShare = deal.amount - fee;

        // 1. تحويل العمولة إلى محفظتك الخاصة مباشرة
        require(usdcToken.transfer(platformOwner, fee), "Fee transfer failed");

        // 2. تحويل باقي القيمة للبائع
        require(usdcToken.transfer(deal.seller, sellerShare), "Seller payment failed");

        emit FundsSettled(sessionId, sellerShare, fee);
    }

    /**
     * @notice استرداد المشتري لكامل أمواله إذا انتهت مدة SLA دون إنجاز
     */
    function refundBuyer(bytes32 sessionId) external {
        EscrowDeal storage deal = deals[sessionId];
        require(deal.status == EscrowStatus.LOCKED, "Deal is not locked");
        
        // إما أن محرك التحكيم قرر الإلغاء أو انتهى مؤقت الأمان الحتمي
        bool isTimedOut = block.timestamp > deal.deadline;
        bool isArbiter = msg.sender == arbiterEngine;
        require(isTimedOut || isArbiter, "SLA deadline has not passed yet and sender is not arbiter");

        deal.status = EscrowStatus.REFUNDED;

        // استرجاع 100% من المبلغ للمشتري دون رسوم
        require(usdcToken.transfer(deal.buyer, deal.amount), "Refund transfer failed");

        emit FundsRefunded(sessionId, deal.buyer, deal.amount);
    }

    /**
     * @notice تحديث عنوان خادم التحكيم عند الحاجة
     */
    function updateArbiter(address newArbiter) external onlyPlatformOwner {
        require(newArbiter != address(0), "Invalid address");
        arbiterEngine = newArbiter;
    }
}

import sqlite3

def cleanup():
    conn = sqlite3.connect("nexus_arbiter.db")
    cursor = conn.cursor()

    # حذف كافة رسائل الاختبار الوهمية دفعة واحدة
    cursor.execute("DELETE FROM messages WHERE sender_agent_id = 'agent:stress_tester'")
    deleted_count = cursor.rowcount

    conn.commit()
    conn.close()

    print(f"[+] تم حذف {deleted_count} رسالة اختبارية بنجاح من قاعدة البيانات.")

if __name__ == "__main__":
    cleanup()
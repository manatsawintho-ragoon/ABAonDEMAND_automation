# ABA on Demand Automator

ทำ course ABA on Demand อัตโนมัติ — Login · ดู Lesson · ตอบ Quiz อัจฉริยะ · จนได้ **100%**

---

## ความต้องการ

| | รายละเอียด |
|---|---|
| OS | Windows 10/11 · macOS · Linux |
| Python | 3.10+ |
| Internet | ต้องการตลอดการทำงาน |

---

## ติดตั้ง (ทำครั้งเดียว)

### Windows
1. ติดตั้ง [Python](https://python.org/downloads/) — ติ๊ก ☑ **Add Python to PATH**
2. ดับเบิ้ลคลิก **`setup.bat`**

### macOS / Linux
```bash
# macOS: brew install python3
chmod +x setup.sh && ./setup.sh
```

---

## เปิดโปรแกรม

| OS | วิธี |
|---|---|
| Windows | ดับเบิ้ลคลิก `run.bat` |
| macOS/Linux | `python3 main.py` หรือ `./run.sh` |

---

## วิธีใช้

1. **เลือก Course** จาก dropdown (บนขวา)
2. **กรอก Email + Password** → กด **+ บันทึก** เพื่อเก็บ profile ไว้
3. เลือก **ความเร็ว** และติ๊ก **ซ่อนเบราว์เซอร์** ถ้าไม่ต้องการเห็นหน้าจอ
4. กด **🔌 Test Login** เพื่อตรวจสอบ password ก่อน
5. กด **▶ Start** — โปรแกรมทำงานอัตโนมัติจนครบ
6. กด **■ Stop** หากต้องการหยุด (หยุดหลัง episode ปัจจุบันเสร็จ)

---

## ฟีเจอร์หลัก

### Quiz อัจฉริยะ
- จำคำตอบด้วย **ข้อความคำถาม** (ไม่ใช่ลำดับ) → รองรับ quiz ที่สลับลำดับคำถาม/ตัวเลือก
- อ่านผล correct/incorrect **ทันทีหลัง Check** → เรียนรู้ทุก attempt
- **Elimination**: ถ้าลองผิด N-1 ตัวแล้ว → ตัวสุดท้ายต้องถูก → บันทึก cache ทันที
- รองรับ radio และ checkbox questions

### Progress & Cache
- บันทึก cache คำตอบใน `data/progress.json` → รอบถัดไปได้ 100% ทันที
- **Atomic write** — ป้องกัน file เสียหายถ้า crash ระหว่างบันทึก
- ข้าม episode ที่ผ่านแล้วอัตโนมัติ

### ความปลอดภัย session
- ตรวจ session หมดอายุ → re-login อัตโนมัติ
- ตรวจ enrollment — แจ้งถ้ายังไม่ได้ enroll

### Lesson Completion (5 วิธี)
1. คลิก form โดยตรง
2. AJAX + sfwd_nonce
3. AJAX + form nonce
4. Seek video (Vimeo / HTML5 / YouTube) → รอ form
5. Force AJAX (fallback)
- หลัง quiz ผ่าน → ลอง lesson อีกครั้ง

---

## UI

### ตารางสี Episode
| สี | ความหมาย |
|---|---|
| เทา ○ | ยังไม่ได้ทำ |
| น้ำเงิน ► | กำลังทำ |
| เขียว ✓ | ผ่าน 100% |
| แดง ✗ | ยังไม่ผ่าน (จะลองใหม่รอบหน้า) |

**คลิกที่ cell** → ดูรายละเอียด (คะแนน, วันที่, จำนวน attempts, lesson status)
**คลิกขวา** → Retry / Reset / เปิด URL

### ปุ่มพิเศษ
| ปุ่ม | ทำอะไร |
|---|---|
| 🔌 Test Login | ตรวจ password ก่อน Start |
| 🗑 Reset ทั้งหมด | ลบ progress ทั้ง course |
| 🗑 Reset Cache คำตอบ | ล้างแค่ cache quiz (progress ยังอยู่) |
| Export Log | บันทึก log เป็น .txt |

### Log Filter
- Filter log ตาม Episode ที่ต้องการ
- ค้นหาด้วย 🔍 search box

---

## ไฟล์สำคัญ

```
run.bat / run.sh      ← เปิดโปรแกรม
setup.bat / setup.sh  ← ติดตั้ง (ครั้งแรก)
data/
  profiles.json       ← email/password profiles
  progress.json       ← progress + cache คำตอบ
  settings.json       ← ค่า speed/headless/dark mode
  errors/             ← screenshot เมื่อ error
assets/
  icon.ico            ← icon โปรแกรม (optional)
```

> ไฟล์ใน `data/` อยู่ในเครื่องเท่านั้น ไม่มีการส่งข้อมูลออกไป

---

## แก้ปัญหา

| ปัญหา | วิธีแก้ |
|---|---|
| โปรแกรมไม่เปิด | รัน `setup.bat` ก่อน |
| Login ล้มเหลว | กด Test Login ตรวจสอบ |
| Quiz ไม่ผ่านหลายรอบ | กด Start ใหม่ (cache ยังอยู่ รอบหน้าดีขึ้น) |
| คะแนนดูผิดปกติ | กด 🗑 Reset Cache คำตอบ แล้ว Start ใหม่ |
| เบราว์เซอร์ค้าง | Stop → เปลี่ยนเป็น `careful` → Start ใหม่ |
| Course 80% ไม่ครบ | รัน Start อีกครั้ง (lesson จะลองซ้ำ) |

---

## สำหรับนักพัฒนา — เพิ่ม Course ใหม่

1. สร้างโฟลเดอร์ `courses/COURSE_ID/`
2. สร้าง `config.py` ตาม pattern เดิม (ดู `courses/uen20367/config.py`)
3. เพิ่ม import ใน `courses/__init__.py`

```python
# courses/__init__.py
from courses.new_course.config import COURSE as _NEW
COURSE_REGISTRY[_NEW.course_id] = _NEW
```

---

*หากพบปัญหา กรุณาแนบ Export Log มาด้วย*

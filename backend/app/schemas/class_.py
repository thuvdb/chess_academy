import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ---------- Class Schemas ----------

class ClassBase(BaseModel):
    name: str
    level: str | None = None
    max_students: int = 30
    schedule_json: dict | None = None
    is_active: bool = True


class ClassCreate(ClassBase):
    center_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None


class ClassUpdate(BaseModel):
    name: str | None = None
    level: str | None = None
    max_students: int | None = None
    schedule_json: dict | None = None
    is_active: bool | None = None
    teacher_id: uuid.UUID | None = None


class ClassRead(ClassBase):
    id: uuid.UUID
    center_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    current_students: int = 0
    teacher_name: str | None = None
    is_enrolled: bool | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Enrollment Schemas ----------

class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID


class EnrollmentRead(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    student_id: uuid.UUID
    enrolled_at: datetime
    status: str
    student_name: str | None = None
    student_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentUpdate(BaseModel):
    status: str


# ---------- Schedule Schemas ----------

class ClassScheduleSlot(BaseModel):
    day: str
    time: str


class ClassScheduleRead(BaseModel):
    class_id: uuid.UUID
    name: str
    level: str | None = None
    teacher_name: str | None = None
    slots: list[ClassScheduleSlot] = []

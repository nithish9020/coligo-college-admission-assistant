from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class College(Base):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Auth
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Basic Information
    college_name: Mapped[str] = mapped_column(String(255), nullable=False)
    college_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    established_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    affiliated_university: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    logo_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Contact Information
    contact_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Social Links
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    facebook: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    twitter: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    instagram: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Accreditation
    accreditation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="college", cascade="all, delete-orphan"
    )
    facilities: Mapped[List["Facility"]] = relationship(
        "Facility", back_populates="college", cascade="all, delete-orphan"
    )
    brochures: Mapped[List["Brochure"]] = relationship(
        "Brochure", back_populates="college", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True
    )

    program_level: Mapped[str] = mapped_column(String(20), nullable=False)  # UG / PG
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    intake_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )  # published / draft

    eligibility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fees: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    course_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    career_opportunities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    college: Mapped["College"] = relationship("College", back_populates="courses")


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    college: Mapped["College"] = relationship("College", back_populates="facilities")


class Brochure(Base):
    __tablename__ = "brochures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    college: Mapped["College"] = relationship("College", back_populates="brochures")

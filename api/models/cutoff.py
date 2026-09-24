from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.core.database import Base


class TNEACutoff(Base):
    __tablename__ = "tnea_cutoffs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    college_code: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    college_name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    branch_code: Mapped[str] = mapped_column(String(16), index=True, default="")
    branch_name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    community: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    cutoff_mark: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    academic_year: Mapped[str] = mapped_column(
        String(16), default="2024", nullable=False
    )

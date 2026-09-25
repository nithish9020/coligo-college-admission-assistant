"""Seed college accounts, courses, and facilities for the Coligo Portal."""

import asyncio
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select  # noqa: E402

from api.core.database import async_session_factory, engine  # noqa: E402
from api.core.security import hash_password  # noqa: E402
from api.models import College, Course, Facility  # noqa: E402

COLLEGES_DATA = [
    {
        "email": "skcet@coligo.com",
        "password": "skcet@password123",
        "college_name": "Sri Krishna College of Engineering and Technology",
        "college_type": "Autonomous",
        "established_year": 1998,
        "affiliated_university": "Anna University, Chennai",
        "contact_person": "Dr. J. Janet (Principal)",
        "contact_email": "admissions@skcet.ac.in",
        "contact_phone": "+91 422 2678001",
        "address": "Kuniamuthur, Palakkad Main Road",
        "city": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "641008",
        "website": "https://www.skcet.ac.in",
        "accreditation": "NAAC 'A' Grade, NBA Accredited, NIRF Ranked",
        "about": (
            "Sri Krishna College of Engineering and Technology (SKCET) is an "
            "autonomous institution accredited with 'A' Grade by NAAC. Established "
            "in 1998 in Coimbatore, SKCET offers premier engineering education across "
            "modern computing, circuit, and core engineering branches "
            "with 95%+ placements."
        ),
        "courses": [
            {
                "program_level": "UG",
                "course_name": "B.E. Computer Science and Engineering",
                "course_code": "CS",
                "duration": "4 Years",
                "intake_capacity": 180,
                "department": "Computer Science and Engineering",
                "fees": "₹55,000 / year (Govt Quota)",
                "eligibility": "10+2 with PCM (TNEA Cutoff)",
                "course_details": (
                    "Covers data structures, algorithms, AI, cloud computing, "
                    "and software development."
                ),
                "career_opportunities": (
                    "Software Engineer, System Architect, Cloud Consultant"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.Tech Information Technology",
                "course_code": "IT",
                "duration": "4 Years",
                "intake_capacity": 180,
                "department": "Information Technology",
                "fees": "₹55,000 / year (Govt Quota)",
                "eligibility": "10+2 with PCM (TNEA Cutoff)",
                "course_details": (
                    "Focused on full-stack web, cybersecurity, networking, and "
                    "distributed systems."
                ),
                "career_opportunities": (
                    "Full Stack Developer, DevOps Engineer, Security Analyst"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.Tech Artificial Intelligence and Data Science",
                "course_code": "AD",
                "duration": "4 Years",
                "intake_capacity": 120,
                "department": "AI and Data Science",
                "fees": "₹55,000 / year (Govt Quota)",
                "eligibility": "10+2 with PCM (TNEA Cutoff)",
                "course_details": (
                    "Deep learning, machine learning, predictive analytics, "
                    "NLP, and Big Data."
                ),
                "career_opportunities": (
                    "AI Specialist, Machine Learning Engineer, Data Scientist"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.E. Electronics and Communication Engineering",
                "course_code": "EC",
                "duration": "4 Years",
                "intake_capacity": 180,
                "department": "Electronics and Communication Engineering",
                "fees": "₹55,000 / year (Govt Quota)",
                "eligibility": "10+2 with PCM (TNEA Cutoff)",
                "course_details": (
                    "VLSI design, embedded systems, IoT, signal processing, "
                    "and communication networks."
                ),
                "career_opportunities": (
                    "VLSI Engineer, Embedded Systems Developer, Telecom Engineer"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.E. Mechanical Engineering",
                "course_code": "ME",
                "duration": "4 Years",
                "intake_capacity": 120,
                "department": "Mechanical Engineering",
                "fees": "₹55,000 / year (Govt Quota)",
                "eligibility": "10+2 with PCM (TNEA Cutoff)",
                "course_details": (
                    "Robotics, CAD/CAM, thermal engineering, manufacturing "
                    "automation, and design."
                ),
                "career_opportunities": (
                    "Design Engineer, Automotive Specialist, Automation Consultant"
                ),
                "status": "published",
            },
        ],
        "facilities": [
            {
                "name": "Central Digital Library",
                "description": (
                    "Over 80,000 volumes, international journals, IEEE digital "
                    "exploration, and 24/7 e-learning access."
                ),
            },
            {
                "name": "High-Performance Computing & AI Lab",
                "description": (
                    "NVIDIA GPU-powered workstations, Apple lab, and dedicated "
                    "enterprise cloud sandbox."
                ),
            },
            {
                "name": "Residential Hostels & Multi-Cuisine Dining",
                "description": (
                    "Separate air-conditioned and standard hostels for men and women "
                    "with hygienic dining halls and Wi-Fi."
                ),
            },
            {
                "name": "Sports & Fitness Complex",
                "description": (
                    "Floodlit football turf, 400m synthetic track, basketball arena, "
                    "and modernized indoor gym."
                ),
            },
        ],
    },
    {
        "email": "psgtech@coligo.com",
        "password": "psgtech@password123",
        "college_name": "PSG College of Technology",
        "college_type": "Govt. Aided Autonomous",
        "established_year": 1951,
        "affiliated_university": "Anna University, Chennai",
        "contact_person": "Dr. K. Prakasan (Principal)",
        "contact_email": "admissions@psgtech.ac.in",
        "contact_phone": "+91 422 2572177",
        "address": "Post Box No. 1611, Peelamedu",
        "city": "Coimbatore",
        "state": "Tamil Nadu",
        "pincode": "641004",
        "website": "https://www.psgtech.edu",
        "accreditation": "NAAC 'A+' Grade, NIRF Top 50, ISO 9001:2015",
        "about": (
            "PSG College of Technology, an ISO 9001:2015 certified institution "
            "established in 1951, is an eminent government-aided autonomous "
            "engineering college affiliated with Anna University. Renowned worldwide "
            "for industry synergy, high research output, and top placements."
        ),
        "courses": [
            {
                "program_level": "UG",
                "course_name": "B.E. Computer Science and Engineering",
                "course_code": "CS",
                "duration": "4 Years",
                "intake_capacity": 120,
                "department": "Computer Science and Engineering",
                "fees": "₹40,000 / year (Govt Aided)",
                "eligibility": "10+2 with PCM (Top TNEA Cutoff)",
                "course_details": (
                    "Advanced computing systems, computer networks, algorithms, "
                    "AI, and cybersecurity."
                ),
                "career_opportunities": (
                    "Core Systems Engineer, Product Developer, AI Researcher"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.Tech Information Technology",
                "course_code": "IT",
                "duration": "4 Years",
                "intake_capacity": 60,
                "department": "Information Technology",
                "fees": "₹40,000 / year (Govt Aided)",
                "eligibility": "10+2 with PCM (Top TNEA Cutoff)",
                "course_details": (
                    "Software engineering, cloud infrastructure, information security, "
                    "and enterprise apps."
                ),
                "career_opportunities": (
                    "Software Architect, Cloud Engineer, Tech Lead"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.E. Electronics and Communication Engineering",
                "course_code": "EC",
                "duration": "4 Years",
                "intake_capacity": 120,
                "department": "Electronics and Communication Engineering",
                "fees": "₹40,000 / year (Govt Aided)",
                "eligibility": "10+2 with PCM (Top TNEA Cutoff)",
                "course_details": (
                    "Semiconductor technology, embedded processors, wireless "
                    "communications, and DSP."
                ),
                "career_opportunities": (
                    "Chip Design Engineer, Hardware Systems Engineer, Firmware Dev"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.E. Robotics and Automation Engineering",
                "course_code": "RA",
                "duration": "4 Years",
                "intake_capacity": 60,
                "department": "Robotics and Automation",
                "fees": "₹75,000 / year (Self Supporting)",
                "eligibility": "10+2 with PCM (TNEA Cutoff)",
                "course_details": (
                    "Industrial robotics, PLC automation, computer vision, "
                    "kinematics, and mechatronics."
                ),
                "career_opportunities": (
                    "Robotics Engineer, Automation Specialist, Control Systems Engineer"
                ),
                "status": "published",
            },
            {
                "program_level": "UG",
                "course_name": "B.E. Mechanical Engineering",
                "course_code": "ME",
                "duration": "4 Years",
                "intake_capacity": 120,
                "department": "Mechanical Engineering",
                "fees": "₹40,000 / year (Govt Aided)",
                "eligibility": "10+2 with PCM (Top TNEA Cutoff)",
                "course_details": (
                    "Precision manufacturing, fluid mechanics, design optimization, "
                    "and automotive engineering."
                ),
                "career_opportunities": (
                    "Manufacturing Specialist, Automotive R&D Engineer, Quality Lead"
                ),
                "status": "published",
            },
        ],
        "facilities": [
            {
                "name": "Siemens Center of Excellence in Automation",
                "description": (
                    "Multi-crore facility housing Siemens PLCs, CNC machines, "
                    "SCADA systems, and industrial robotics."
                ),
            },
            {
                "name": "Dr. G. R. Damodaran Central Library",
                "description": (
                    "Sprawling central library housing 250,000+ technical volumes, "
                    "patents, and global research databases."
                ),
            },
            {
                "name": "PSG Tech Campus Hostels",
                "description": (
                    "Comfortable living accommodations for over 4,000 students "
                    "with dedicated study halls and high-speed LAN."
                ),
            },
            {
                "name": "Indoor Sports Stadium & Gymnasium",
                "description": (
                    "State-of-the-art indoor badminton courts, table tennis, "
                    "basketball arena, and fitness center."
                ),
            },
        ],
    },
]


async def seed_colleges():
    print("=" * 60)
    print("Seeding College Accounts, Courses & Facilities...")
    print(f"Target DB: {engine.url.render_as_string(hide_password=True)}")
    print("=" * 60)

    async with async_session_factory() as db:
        for c_data in COLLEGES_DATA:
            email = c_data["email"].lower()
            stmt = select(College).where(College.email == email)
            existing = (await db.execute(stmt)).scalar_one_or_none()

            if existing:
                print(f" -> Updating College: {c_data['college_name']} ({email})")
                college = existing
                college.hashed_password = hash_password(c_data["password"])
                college.is_active = True
                college.college_type = c_data["college_type"]
                college.established_year = c_data["established_year"]
                college.affiliated_university = c_data["affiliated_university"]
                college.contact_person = c_data["contact_person"]
                college.contact_email = c_data["contact_email"]
                college.contact_phone = c_data["contact_phone"]
                college.address = c_data["address"]
                college.city = c_data["city"]
                college.state = c_data["state"]
                college.pincode = c_data["pincode"]
                college.website = c_data["website"]
                college.accreditation = c_data["accreditation"]
                college.about = c_data["about"]
            else:
                print(f" -> Creating College: {c_data['college_name']} ({email})...")
                college = College(
                    email=email,
                    hashed_password=hash_password(c_data["password"]),
                    college_name=c_data["college_name"],
                    college_type=c_data["college_type"],
                    established_year=c_data["established_year"],
                    affiliated_university=c_data["affiliated_university"],
                    contact_person=c_data["contact_person"],
                    contact_email=c_data["contact_email"],
                    contact_phone=c_data["contact_phone"],
                    address=c_data["address"],
                    city=c_data["city"],
                    state=c_data["state"],
                    pincode=c_data["pincode"],
                    website=c_data["website"],
                    accreditation=c_data["accreditation"],
                    about=c_data["about"],
                    is_active=True,
                )
                db.add(college)
                await db.flush()

            # Seed Courses
            for course_dict in c_data["courses"]:
                c_stmt = select(Course).where(
                    Course.college_id == college.id,
                    Course.course_name == course_dict["course_name"],
                )
                existing_course = (await db.execute(c_stmt)).scalar_one_or_none()
                if not existing_course:
                    new_course = Course(
                        college_id=college.id,
                        program_level=course_dict["program_level"],
                        course_name=course_dict["course_name"],
                        course_code=course_dict["course_code"],
                        duration=course_dict["duration"],
                        intake_capacity=course_dict["intake_capacity"],
                        department=course_dict["department"],
                        fees=course_dict["fees"],
                        eligibility=course_dict["eligibility"],
                        course_details=course_dict["course_details"],
                        career_opportunities=course_dict["career_opportunities"],
                        status=course_dict["status"],
                    )
                    db.add(new_course)

            # Seed Facilities
            for fac_dict in c_data["facilities"]:
                f_stmt = select(Facility).where(
                    Facility.college_id == college.id,
                    Facility.name == fac_dict["name"],
                )
                existing_fac = (await db.execute(f_stmt)).scalar_one_or_none()
                if not existing_fac:
                    new_fac = Facility(
                        college_id=college.id,
                        name=fac_dict["name"],
                        description=fac_dict["description"],
                    )
                    db.add(new_fac)

        await db.commit()
        print("\n✓ Both colleges, courses, and facilities successfully committed!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_colleges())

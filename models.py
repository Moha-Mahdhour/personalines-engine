from typing import Optional, List
from pydantic import BaseModel

# Section Task Insert
class Record_Meta_data(BaseModel):
    id: int
    UserID: str
    FileName: str
    Status: str
    LinkedinField: str
    
    

class Task(BaseModel):
    
    record: Record_Meta_data

class DateModel(BaseModel):
    day: int
    month: int
    year: int
    
    def __repr__(self) -> str:
        return f"year: {self.year}, month: {self.month}"

    def __str__(self) -> str:
        return self.__repr__()

class ExperienceModel(BaseModel):
    starts_at: DateModel
    ends_at: Optional[DateModel] = "Present"
    company: str
    title: str
    description: Optional[str]
    location: Optional[str]
    
    def __repr__(self) -> str:
        string = "\n"
        string += f"\t\tStarted: {self.starts_at}\n"
        string += f"\t\tEnded: {self.ends_at}\n"
        string += f"\t\tCompany: {self.company}\n"
        string += f"\t\tTitle: {self.title}\n"
        string += f"\t\tDescription: {self.description}\n"
        string += f"\t\tLocation: {self.location}\n"
        
        return string
    
    def __str__(self) -> str:
        return self.__repr__()

class CertificationModel(BaseModel):
    starts_at: DateModel
    ends_at: Optional[DateModel]
    name: str
    
    def __repr__(self) -> str:
        string = "\n"
        string += f"\t\tStarted: {self.starts_at}\n"
        string += f"\t\tEnded: {self.ends_at}\n"
        string += f"\t\tCertification Name: {self.name}\n"
        
        return string
    
    def __str__(self) -> str:
        return self.__repr__()
    
class EducationModel(BaseModel):
    starts_at: DateModel
    ends_at: Optional[DateModel]
    field_of_study: str
    degree_name: str
    school: str
    description: Optional[str]
    
    def __repr__(self) -> str:
        string = "\n"
        string += f"\t\tStarted: {self.starts_at}\n"
        string += f"\t\tEnded: {self.ends_at}\n"
        string += f"\t\tField of Study: {self.field_of_study}\n"
        string += f"\t\tDegree Name: {self.degree_name}\n"
        string += f"\t\tschool: {self.school}\n"
        string += f"\t\tDescription: {self.description}\n"
        
        return string
    
    def __str__(self) -> str:
        return self.__repr__()
        

class LinkedInProfileModel(BaseModel):
    public_identifier: str
    first_name: str
    last_name: str
    full_name: str
    occupation: str
    headline: str
    summary: str
    country: str
    country_full_name: str
    city: str
    state: str
    experiences: List[ExperienceModel]
    education: List[EducationModel]
    certifications: List[CertificationModel]
    
    def __repr__(self) -> str:
        string = "\n"
        string += f"Full Name: {self.full_name}\n"
        string += f"Occupation: {self.occupation}\n"
        string += f"Headline: {self.headline}\n"
        string += f"Summary: {self.summary}\n"
        string += f"City and State: {self.city}, {self.state}\n"
        string += f"Country: {self.country}\n"
        
        string += f"Experiences List:\n"
        for exp in self.experiences:
            string += f"\tExperience:\n"
            string += f"\t\t{str(exp)}\n"
           
        string += f"Education List:\n"
        for edu in self.education:
            string += f"\tEducation:\n"
            string += f"\t\t{str(edu)}\n"
            
        string += f"Certifications List:\n"
        for cert in self.certifications:
            string += f"\tCertification:\n"
            string += f"\t\t{str(cert)}\n"
        
        
        
        return string

    def __str__(self) -> str:
        return self.__repr__()

    @classmethod
    def format_dates(cls, data: dict):
        # Process experiences
        experiences = []
        for exp in data['experiences']:
            starts_at = exp['starts_at']
            ends_at = exp['ends_at']
            starts_at_date = DateModel(**starts_at)
            ends_at_date = DateModel(**ends_at) if ends_at else "Present"
            experience = ExperienceModel(
                starts_at=starts_at_date,
                ends_at=ends_at_date,
                company=exp['company'],
                title=exp['title'],
                description=exp['description'],
                location=exp['location']
            )
            experiences.append(experience)
        
        # Process certifications
        certifications = []
        for cert in data['certifications']:
            starts_at = cert['starts_at']
            ends_at = cert['ends_at']
            starts_at_date = DateModel(**starts_at)
            ends_at_date = DateModel(**ends_at) if ends_at else None
            certification = CertificationModel(
                starts_at=starts_at_date,
                ends_at=ends_at_date,
                name=cert['name']
            )
            certifications.append(certification)
            
        education = []
        for edu in data['education']:
            starts_at = edu['starts_at']
            ends_at = edu.get('ends_at')
            starts_at_date = DateModel(**starts_at)
            ends_at_date = DateModel(**ends_at) if ends_at else None
            education_item = EducationModel(
                starts_at=starts_at_date,
                ends_at=ends_at_date,
                field_of_study=edu['field_of_study'],
                degree_name=edu['degree_name'],
                school=edu['school'],
                school_linkedin_profile_url=edu.get('school_linkedin_profile_url'),
                school_facebook_profile_url=edu.get('school_facebook_profile_url'),
                description=edu.get('description'),
                logo_url=edu.get('logo_url'),
                grade=edu.get('grade'),
                activities_and_societies=edu.get('activities_and_societies')
            )
            education.append(education_item)

        # Construct the LinkedInProfileModel
        return cls(
            public_identifier=data['public_identifier'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            full_name=data['full_name'],
            occupation=data['occupation'],
            headline=data['headline'],
            summary=data['summary'],
            country=data['country'],
            country_full_name=data['country_full_name'],
            city=data['city'],
            state=data['state'],
            experiences=experiences,
            education=data['education'],
            certifications=certifications
        )

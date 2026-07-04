<div align="center">

<!-- Animated Wave Header -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0D0D0D,100:FF7A00&height=220&section=header&text=StudyMart%20Backend&fontSize=50&fontColor=FF7A00&animation=fadeIn&fontAlignY=38&desc=FastAPI%20%2B%20MongoDB%20Powered%20Study%20Marketplace%20API&descAlignY=58&descSize=18" width="100%"/>

<!-- Typing SVG -->
<a href="#">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=26&duration=3000&pause=800&color=FF7A00&center=true&vCenter=true&width=650&lines=Buy+%26+Sell+Study+Materials+Seamlessly;Built+with+FastAPI+%2B+MongoDB;Secure+%7C+Scalable+%7C+Student-First" alt="Typing SVG" />
</a>

<br/>

<!-- Badges -->
<p>
  <img src="https://img.shields.io/badge/FastAPI-0D0D0D?style=for-the-badge&logo=fastapi&logoColor=FF7A00" />
  <img src="https://img.shields.io/badge/MongoDB-0D0D0D?style=for-the-badge&logo=mongodb&logoColor=FF7A00" />
  <img src="https://img.shields.io/badge/Python-0D0D0D?style=for-the-badge&logo=python&logoColor=FF7A00" />
  <img src="https://img.shields.io/badge/JWT-0D0D0D?style=for-the-badge&logo=jsonwebtokens&logoColor=FF7A00" />
  <img src="https://img.shields.io/badge/Cloudinary-0D0D0D?style=for-the-badge&logo=cloudinary&logoColor=FF7A00" />
</p>

<p>
  <img src="https://img.shields.io/github/stars/AakashKavediya/studymart_backend?style=flat-square&color=FF7A00&labelColor=0D0D0D" />
  <img src="https://img.shields.io/github/forks/AakashKavediya/studymart_backend?style=flat-square&color=FF7A00&labelColor=0D0D0D" />
  <img src="https://img.shields.io/github/last-commit/AakashKavediya/studymart_backend?style=flat-square&color=FF7A00&labelColor=0D0D0D" />
  <img src="https://img.shields.io/badge/status-active--development-FF7A00?style=flat-square&labelColor=0D0D0D" />
</p>

</div>

<br/>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" height="2px">

## 🟠 About The Project

**StudyMart Backend** is the API engine behind a full-stack study-materials marketplace where students can **buy, sell, and discover** notes, guides, and academic resources. Built with **FastAPI** for speed and **MongoDB** for flexible document storage, it powers the companion frontend — **StudyBazar** (Next.js + Redux Toolkit).

```diff
+ Fast async API layer with FastAPI
+ Flexible schema-less storage via MongoDB
+ Secure JWT-based authentication
+ Cloudinary-powered media/image handling
```

<br/>

## ⚡ Tech Stack

<div align="center">

| Layer | Technology |
|:--|:--|
| 🖤 **Framework** | FastAPI (Python) |
| 🟠 **Database** | MongoDB |
| 🖤 **Auth** | JWT (JSON Web Tokens) |
| 🟠 **Media Storage** | Cloudinary |
| 🖤 **Frontend (companion)** | Next.js + Redux Toolkit |

</div>

<br/>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" height="2px">

## 🚀 Features

- 🔐 **Authentication & Authorization** — secure JWT-based login/signup flow
- 📚 **Study Material Marketplace** — upload, list, and browse academic resources
- 🖼️ **Media Handling** — image/document uploads via Cloudinary
- 🔍 **Search & Filter** — find materials by subject, category, or keyword
- ⚙️ **RESTful API Architecture** — clean, modular FastAPI route structure
- 🗃️ **MongoDB Integration** — flexible, scalable document-based storage

<br/>

## 🖥️ Getting Started

### Prerequisites

```bash
Python 3.10+
MongoDB (local or Atlas)
pip / virtualenv
```

### Installation

```bash
# Clone the repository
git clone https://github.com/AakashKavediya/studymart_backend.git

# Navigate into the project
cd studymart_backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root directory:

```env
MONGO_URI=your_mongodb_connection_string
JWT_SECRET_KEY=your_jwt_secret
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

> ⚠️ **Never commit your `.env` file.** Add it to `.gitignore` and rotate any keys that were previously exposed.

### Run the Server

```bash
uvicorn main:app --reload
```

The API will be live at **`http://127.0.0.1:8000`**
Interactive docs available at **`http://127.0.0.1:8000/docs`**

<br/>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" height="2px">

## 📂 Project Structure

studymart_backend/
├── app/
│   ├── routes/          # API route definitions
│   ├── models/          # MongoDB schemas / Pydantic models
│   ├── services/        # Business logic layer
│   ├── utils/           # Helper functions
│   └── core/            # Config, security, DB connection
├── requirements.txt
├── main.py
└── .env.example

<br/>

## 🧭 API Overview

| Method | Endpoint | Description |
|:--|:--|:--|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Authenticate & receive JWT |
| `GET` | `/materials` | Fetch all study materials |
| `POST` | `/materials` | Upload a new material |
| `GET` | `/materials/{id}` | Get details of a specific material |

<br/>

## 🗺️ Roadmap

- [x] Core authentication system
- [x] Material upload & listing
- [ ] Payment gateway integration
- [ ] Rating & review system
- [ ] Admin dashboard APIs
- [ ] Rate limiting & caching layer

<br/>

<img src="https://user-images.githubusercontent.com/74038190/212284100-561aa473-3905-4a80-b561-0d28506553ee.gif" width="100%" height="2px">

## 🤝 Contributing

Contributions make the open-source community amazing. Any contributions are **greatly appreciated**.

```bash
1. Fork the project
2. Create your feature branch (git checkout -b feature/AmazingFeature)
3. Commit your changes (git commit -m 'Add some AmazingFeature')
4. Push to the branch (git push origin feature/AmazingFeature)
5. Open a Pull Request
```

<br/>

## 👤 Author

<div align="center">

**Aakash Kavediya** <br/>
**Khushi Jamnare**

<img src="https://img.shields.io/badge/GitHub-0D0D0D?style=for-the-badge&logo=github&logoColor=FF7A00" />

</div>

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:FF7A00,100:0D0D0D&height=150&section=footer"/>
</div>

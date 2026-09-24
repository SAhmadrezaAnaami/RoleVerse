# RoleVerse

## About RoleVerse

this is a minimalist clone of character.ai but with better chatgpt like style and UI.
in this project instead of chatting with models you chat with characters with soul, persona, names, history and extra.
users do role play chats with every well known characters (defined by admins) they want.
users also have access to a character market place too.

## Getting Started

### Local development

Requirements: Python 3.10 or newer. Node.js and npm are not required.

1. Create and activate a Python virtual environment.
2. Install the backend and development dependencies:

```powershell
cd backend
python -m pip install -e ".[dev]"
```

3. Copy the environment template when local configuration is needed:

```powershell
Copy-Item .env.example .env
```

4. Start the application:

```powershell
python -m uvicorn app.main:app --reload
```

5. Open `http://127.0.0.1:8000/`.

Run the backend tests with:

```powershell
cd backend
python -m pytest
```

The first development slice uses deterministic client data. Real OTP, database persistence, OpenAI-compatible generation, and the admin panel are delivered in later sections.

## Rules

- users does not plan or payment to chat, our platfor is free to use.
- sign up and login is needed (phone number verification by OTP send into console for dev, mock it in console for now).
- admin can log in and manage chaarcters and open ai compatible models behind the scene.
- there is a god user defind in .env that can manage and promote users to admins.
- compelet admin panel with comprehensive simple management of everything (characters, users, chats, Openai compatible providers and models, Usage by users, input output cost, specefic user cost and chats, ban user, config the global system setting, rate limit settings and ...)
- users have a global rate limit on how many request they send.

## UI/UX
- it must be looking good, persian and english language and light and dark mode.
- chat render support both rtl and ltr for persian and english.
- chat and history and user setting and login page is familiar to ChatGPT and it is profficional like ChatGPT.
- client must look modern and prettty like na umbrella or disney land (colorfull and alive).
- UX look similar to ChatGPT.
- what ever other Ideas is acceptable
- you can use UI UX Pro Max Skill for this section.

## Stack

- python + sqlalchemy + alembic + fastapi + sqlite + openai SDK
- html, css, javascript, tailwind (no npm or nodejs is needded use static tailwind cdn)
- good pretty fonts
- every resource must be static
- seperate client and backend folders in root for backend and client files.
- keep code very structured and functional, seperate concepts as much as possible in small files.
- have schemas for both inputs, outputs, database calls and everything else.
- have an database engine that uses schemas for qwerys to reduce database services codes.
- do not add comment in code (no need for it.)

## Git

- do not push in main branch
- frequently add branch and push code to them for every section you do, do not remove old branches.
- add commits for every single files.
- merge your tested branches frequently to the main (yourself).
- keep local with my github updated.
- have verson and taging too.
- keep changelog for branches and versions.
- keep everything proffisional in github.

## multi agent

- you can produce as much as agent you want to do tasks.
- plese use subagents to do tasks (testing, arch, documenting, coding all together.)
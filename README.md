# Hojathon

Build agents that don't just respond — they act.

Hojathon is an agentic AI hackathon. Teams build systems that can reason, plan, call tools or APIs, and carry out multi-step tasks on their own — not just chatbots that answer a single prompt. This repository is the official starter and submission template: fork it, build your project inside your fork, and submit your final work back here through a Pull Request.

There's no required stack. Build your agent with any language, any framework, any model provider or orchestration approach — LangChain, a custom agent loop, raw API calls, whatever gets the job done. This repo itself contains no code. It's just the structure and docs every team needs so judges can actually run and evaluate what you built.

---

## Getting Started

1. **Fork this repository** — click "Fork" at the top of this page, then click the green **"Create fork"** button on the page that follows to confirm.
2. **Clone your fork** to your computer:
   ```bash
   git clone https://github.com/<your-username>/<your-fork>.git
   ```
3. **Read through this README and the [`docs/`](docs/) folder in full** before you write any code, so you understand the rules, the workflow, and what your final submission needs to include.
4. **Add your teammates as collaborators** on your fork (GitHub → Settings → Collaborators) so everyone can push directly.
5. **Build your project** inside your fork, using whatever stack fits your idea.
6. **Commit and push regularly** — don't wait until the deadline to save your work.
7. **Fill in the project documentation** (see [Project Documentation](#project-documentation) below and the [`docs/`](docs/) folder).
8. **Open your final Pull Request** back to this repository before the deadline.

---

## Team Information

Fill this in as soon as your team is formed.

**Team ID:**

**Team Name:**

**Team Members:**

1. Name
2. Name
3. Name

**Project Name:**

> Teams may have **1, 2, or 3 members**.

---

## Project Documentation

Replace the placeholders below with your own project's details — this is what judges will actually read.

### Project Name

Seva — multilingual civic-service action agent

### Team

### Problem Statement

What problem are you solving, and why does it call for an agent rather than a static script or a plain UI?

Government forms are difficult to navigate when the citizen is most comfortable speaking Malayalam. Seva turns a short voice or typed request into a guided task: it identifies the service, collects required facts, checks eligibility, prepares the form, and reports status. This requires an agent because the next step depends on the service and facts already known.

### Proposed Solution

Explain your solution and how your agent approaches the problem.

Seva is a Malayalam/English voice-and-text assistant with a private account for every citizen. It maintains a scoped profile and application history for the signed-in user, uses service-specific form schemas, and gives a concise update after each step.

For a production official-portal connection, Seva must use that portal's approved API or browser integration. It shows the completed form and requires explicit citizen approval before submission. OTP, CAPTCHA, payment, and identity challenges remain with the citizen; the agent never bypasses them.

### Key Features

* Malayalam and English typed conversations, browser voice input, and spoken responses.
* Individual password-protected accounts; all profiles, conversations, and application records are scoped to the authenticated user.
* Guided eligibility/form workflow and private status updates, with a clear approval boundary for official sites.

### Technology Stack

Describe whatever stack you chose. None of the categories below are required — leave out or add rows as needed.

| Category | Technology |
| -------- | ---------- |
| Frontend | Vanilla HTML, CSS, JavaScript, PWA |
| Backend  | FastAPI |
| Database | SQLite demo (use a managed encrypted database in production) |
| AI/ML    | Tool-calling LLM with ASR/TTS adapters |
| APIs     | Approved official-government portal integrations |
| Other    | PBKDF2 password hashing and expiring opaque tokens |

### How It Works

Explain your agent's architecture: what tools or APIs it can call, how it plans and decides what to do next, and what a full run through your system looks like. Add diagrams if they help.

```
Citizen (Malayalam/English voice or text)
  → account-authenticated Seva session
  → intent + service lookup → eligibility / field-by-field form workflow
  → review + citizen approval → approved official portal connection
  → portal receipt/status → private application updates
```

This repository includes a safe local portal simulator for the form/tracking experience. Connecting a live portal needs each department's written authorization and approved integration; it is deliberately not a CAPTCHA or OTP circumvention tool.

### Setup & Installation

Replace this section with your project's actual setup instructions.

### Running the Project

Explain exactly how judges can run and use the project.

---

## Participant Rules

* Teams must contain **1–3 members**.
* Teams may use **any technology stack**.
* Teams should commit their work regularly.
* Do **not** commit passwords, API keys, tokens, or other secrets.
* The final state of the repository at the submission deadline will be considered for judging.
* The final Pull Request must be submitted before the official deadline.
* Participants are responsible for ensuring their project can be evaluated.

---

## GitHub Workflow

```
Official Hojathon Repository
        ↓
      Fork
        ↓
   Team's Fork
        ↓
  Build Project
        ↓
  Commit & Push
        ↓
 Complete README
        ↓
   Final PR
        ↓
   Organizers
        ↓
    Judges
```

Don't open a Pull Request for every change. Work normally inside your own fork, committing and pushing as often as you like — only open a Pull Request to the official repository when you're ready to make your **final submission**.

---

## Final Pull Request

When your project is ready, open a Pull Request from your fork's default branch into the official Hojathon repository.

**PR title format:**

```
[TEAM-ID] Project Name
```

**Example:**

```
[TEAM-042] Smart Campus Assistant
```

**The PR description must contain:**

* Team ID
* Team name
* Team members
* Project name
* Problem statement
* Solution
* Technology stack
* Demo URL
* Demo video
* Special instructions for judges

See [`docs/SUBMISSION.md`](docs/SUBMISSION.md) for the full submission checklist and process, and use the [Pull Request template](.github/PULL_REQUEST_TEMPLATE.md) when you open your final PR.

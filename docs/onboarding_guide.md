# Founder's Guide: Navigating the Werk Platform

Welcome to Werk, your AI-orchestrated development environment. This guide will help you understand how to interact with your virtual team and manage your software projects.

## 1. Getting Started: Initialization
To begin a new project, navigate to the "Create Project" section and provide your **Business Plan**.
- **Tip:** Be as detailed as possible about your target audience, core features, and any specific technical constraints you might have.
- The **Functional Consulting Lead** agent will automatically pick up your plan and begin the analysis.
- Within minutes, it will generate a **Product Requirements Document (PRD)** and **User Stories**.
- You will receive a WebSocket notification in the activity feed when these are ready for your review.

## 2. The Hybrid Dashboard
Your main interface is a combination of real-time communication and visual project management.
- **Agent Chat:** On one side, you can chat directly with the **Lead Agent**. Use this to provide feedback, ask for status updates, or clarify requirements.
- **Kanban Board:** On the other side, you can see the real-time status of every task.
    - **Backlog:** Tasks defined but not yet started.
    - **In Progress:** Tasks currently being worked on by a specific agent.
    - **Review:** Completed tasks waiting for approval.
    - **Done:** Fully implemented and verified features.

## 3. Human-in-the-Loop: Sign-offs
While Werk is highly autonomous, critical milestones require your explicit approval to ensure the project remains aligned with your vision.
- When a task reaches the **"Approval Required"** state (e.g., after PRD generation or before final Deployment), you will see a **"Sign-off"** button on the Kanban card.
- **How to Approve:**
    1. Click the task card to see the detailed result and artifact links.
    2. Click the **"Approve"** button. This will trigger the next stage in the LangGraph orchestrator (e.g., moving from Requirements to Architecture).
- **How to Reject:**
    1. Click the **"Reject"** button.
    2. Provide feedback in the chat or the rejection prompt. The Lead Agent will then re-process the task based on your input.

## 4. Understanding Your Virtual Team
- **Functional Lead:** Your primary point of contact for product scope and UX.
- **Technical Lead:** Handles architecture and ensures code quality.
- **Software Engineer:** Implements the actual features and tests.
- **QA Engineer:** Ensures the platform is secure and bug-free.

## 5. Monitoring Progress & Resources
- **Autonomy Score:** Tracked on your dashboard, showing how much of the work is being handled autonomously by agents.
- **Cycle Time:** Displays the average time from your initial idea to production-ready code.
- **Credits:** Monitor your LLM and compute usage in real-time to manage your project budget.

---
*Werk: Turning ideas into software, one agent at a time.*

# Werk Platform — End-to-end walkthrough

A 10-minute happy path from a signed SOW to downloadable deliverables.

## 0. Start the platform

```bash
cd infrastructure
docker-compose up -d --build
docker-compose exec ollama ollama pull llama3.2   # one-time
```

Open **http://localhost:5173**. You land on the **Agent Canvas** showing the global agent roster.

## 1. Deploy a team from the SOW

1. Click **Deploy from SOW** (top-right of the canvas).
2. Upload **`docs/SAMPLE_SOW.md`** and click **Analyze SOW**.
3. The **Project parameters** form is auto-filled from the document:
   - Approach: **hybrid** · Releases: **3** · Test cycles: **5**
   - Countries: **United States, United Kingdom** · Budget: **750000** · Duration: **12** ·
     Compliance: **GDPR, SOC2**
4. Below it, the **recommended team** is staffed from those parameters — note **DevOps** (3
   releases / 12 months), **UX** (2 countries), **Business Logic** (budget + compliance), and
   **3 Tester agents** (5 test cycles, capped at 3). Each line shows *why* it was staffed.
5. Adjust any parameter and click **Update recommended team from parameters** to see the team
   change. Optionally open **Configure parameters (advanced)** to add your own parameter.
6. Click **Deploy N agents**.

## 2. Explore the deployed team

The canvas switches to **Team · Project Helios…** (use the team selector to switch back to the
global roster). Each agent is a card with live status; click one to open its panel.

## 3. Tune an agent

In an agent's panel:
- **Instructions** → Edit → rewrite its system prompt → **Save** (applies immediately).
- **Examples** → add a "good output" sample so it matches your house style.
- **Chat** → ask it about its part of the work.

## 4. Run a single task

In the agent's panel, under **Assigned work**, click **▶ Run** on its kickoff task. The agent does
the work with the local model, the card shows **Working**, and the task moves to **In Review** with
a **View output** toggle. Approve it to mark it done.

## 5. Run the full pipeline

Go to **Projects → Project Helios → Run full workflow**. The seven agents work through
Requirements → UX → Architecture → Development → Testing, then **pause at the review gate**.
Review the stage outputs, then **Approve & deploy** (runs Deploy) or **Reject** (stops for rework).

> On a CPU-bound local model the full run takes a few minutes; it runs in the background and the
> board updates live.

## 6. Download the deliverables

Scroll to the **Artifacts** panel on the project. Every stage produced a named file —
`functional_requirements.md`, `ux_design.md`, `architecture.md`, `implementation.md`,
`test_plan.md`, `deployment.md`. Click **Download** on any of them.

---

That's the loop: **upload an SOW → a tailored team is staffed → configure each agent → run the
lifecycle → download the deliverables.**

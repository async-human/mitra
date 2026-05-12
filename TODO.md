Three things are ready to build, in order of impact:

1. Proactive Job Alerts ← I'd do this next

When a new job is added, Mitra automatically WhatsApps every candidate whose signals match it. Right now Mitra is silent until someone messages first — this flips it into an actual agent.

What it needs: a notify_matching_candidates function that runs as a background task on job creation/update, embeds the new job, does a reverse vector search (job → top N candidates), and fires WhatsApp messages. One or two sessions per matched candidate of the form: "Hey, just got a Series A fintech role — React + Node, ₹45-65L. Fits what you told me. Want an intro?"

This is the viral engine. Candidates who get unprompted good matches tell friends.

2. Ghosted Intro Follow-up to Candidate

When an intro flips to ghosted (7 days, no founder response — we auto-mark this now), the candidate currently hears nothing. They deserve a WhatsApp: "[Company] hasn't replied yet. I'm following up with them. Here are 2 more roles in the meantime." Plus a proactive re-intro to the founder.

Smaller build, closes a trust gap.

3. Admin Metrics Endpoint

A single GET /admin/metrics response: total intros, broken down by status, per-week trend, and intro→hire conversion rate. Right now you can't answer the single most important question about your own business without querying Postgres directly.


IS IT POSSIBLE TO IMPLEMENT A WORKFLOW WHERE THE FOUNDER JUST SAYS TO POST A NEW JOB ON THEIR BEHALF, AND THE AGENT TAKES THAT GOAL AND EXECUTES END TO END AND POSTS THE JOB ON THEIR BEHALF, IN THIS WAY WE CAN AUTOMATE THE WORKFLOW OF JOB POSTING ON FOUNDERS BEHALF
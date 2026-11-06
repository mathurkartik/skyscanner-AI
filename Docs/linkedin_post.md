# LinkedIn Post — Draft

---

I wanted to understand how AI could reshape travel planning. So instead of writing a PRD, I built the product.

An AI Travel Planner that does what ChatGPT, Gemini, and Claude can't:

- Live bookable flights from airline systems (actual fares, not estimates)
- Per-day hotel options with ratings and smart swap suggestions
- The AI picks flights, trains, ferries, or drives per segment based on the route
- Interactive itinerary with map pins, budget breakdown, and booking links

But building it wasn't the interesting part. Auditing it was.

I ran 26 edge case tests and a full frontend audit. Found 46 bugs. Two patterns stood out:

1. Stale demo content was leaking into every trip. Planning Paris? The app was showing tips about Icelandic fuel cards.

2. Four parts of the system each handled currency differently. One wrong symbol and users stop trusting every number on the page.

These aren't code bugs. They're product bugs.

What I took away:

- AI output quality is a product problem, not a model problem. The LLM was capable — the pipeline around it was dropping context and defaulting to stale data.
- Edge cases reveal your architecture. "Weekend getaway" crashed because the system didn't know "weekend" means 2 days. That's not obscure — that's how real users talk.
- The gap between demo and product is massive. Getting AI to plan one trip takes an afternoon. Handling 26 different trip types without embarrassing itself takes weeks.

Live demo: https://skyscanner-ai-beige.vercel.app
Code: https://github.com/mathurkartik/skyscanner-AI

#ProductManagement #AI #TravelTech #MultiAgentAI #BuildingInPublic

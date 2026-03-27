from __future__ import annotations

from langchain.chains import LLMChain, RetrievalQA
from langchain.prompts import PromptTemplate


def create_intake_chain(llm):
    prompt = PromptTemplate(
        input_variables=["incomplete_student_profile"],
        template="""Given this incomplete student profile:
{incomplete_student_profile}

Generate 3-5 clarifying questions to collect:
1. Completed courses (with grades if available)
2. Target major/program
3. Catalog year
4. Target term (Fall/Spring)
5. Max credits/courses per term

Return a JSON array of concise questions.""",
    )
    return LLMChain(llm=llm, prompt=prompt)


def create_retrieval_chain(llm, retriever):
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )


def create_eligibility_chain(llm):
    prompt = PromptTemplate(
        input_variables=["student_courses", "target_course", "catalog_info"],
        template="""You are a catalog-grounded course planning assistant.

STUDENT COMPLETED: {student_courses}
TARGET COURSE: {target_course}
CATALOG INFORMATION: {catalog_info}

Rules:
- Use only the provided catalog information.
- If evidence is incomplete or ambiguous, say "Need More Info".
- Every factual claim must be traceable to the catalog information.

Return ONLY this structure:
DECISION: [Eligible | Not Eligible | Need More Info]
WHY: [Requirements/prerequisites satisfied or missing]
CITATIONS: [List specific sources/sections]
NEXT_STEP: [What the student should do next]
ASSUMPTIONS: [Anything not in catalog or needing verification]""",
    )
    return LLMChain(llm=llm, prompt=prompt)


def create_plan_chain(llm):
    prompt = PromptTemplate(
        input_variables=["student_profile", "program_requirements", "available_courses"],
        template="""You are generating a next-term plan grounded only in catalog evidence.

STUDENT PROFILE:
{student_profile}

PROGRAM REQUIREMENTS:
{program_requirements}

RETRIEVED CATALOG EVIDENCE:
{available_courses}

Rules:
- Ask for clarification if required profile fields are missing.
- Do not assume semester availability unless the catalog explicitly states it.
- For each proposed course, explain why it fits and why prerequisites appear satisfied.
- Include a separate assumptions / not-in-catalog section.

Return JSON with this shape:
{{
  "answer": "...",
  "plan": [
    {{
      "course": "COMPSCI 161",
      "why": "...",
      "citations": ["[Source: ...]"]
    }}
  ],
  "clarifying_questions": [],
  "assumptions": []
}}""",
    )
    return LLMChain(llm=llm, prompt=prompt)


def create_verifier_chain(llm):
    prompt = PromptTemplate(
        input_variables=["response", "source_documents"],
        template="""Review this draft response:
{response}

Against these source documents:
{source_documents}

Check:
1. Every claim has a citation.
2. No unsupported assumptions are stated as fact.
3. Prerequisites and requirements are interpreted correctly.
4. The response format contains:
   - Answer / Plan
   - Why
   - Citations
   - Clarifying questions
   - Assumptions / Not in catalog

Return either:
- VERIFIED
or
- A short bullet list of problems found.""",
    )
    return LLMChain(llm=llm, prompt=prompt)


"""
AgentLine — EPDS (Edinburgh Postnatal Depression Scale) scoring.

Scoring is done here in code, never by the LLM, so results are deterministic
and auditable. 10 items, each contributes 0-3, total range 0-30.

Items 1, 2 and 4 are scored in option order (first option = 0).
Items 3 and 5-10 are reverse scored (first option = 3).
Item 10 asks about self-harm — any answer other than "Never" raises a flag
that must trigger human escalation regardless of the total score.

Hindi text is provided for the Hindi/Hinglish call flow. These translations
are for the prototype and must be clinically reviewed before real use.
"""

NUM_QUESTIONS = 10
MAX_SCORE = 30
NORMAL_SCORED = frozenset({1, 2, 4})
SELF_HARM_QUESTION = 10

# Risk band cutoffs on the 0-30 total.
LOW_MAX = 9
MEDIUM_MAX = 12

QUESTIONNAIRE: list[dict] = [
    {
        "no": 1,
        "reverse_scored": False,
        "text": {
            "en": "I have been able to laugh and see the funny side of things",
            "hi": "मैं हँस पाई हूँ और चीज़ों का मज़ेदार पहलू देख पाई हूँ",
        },
        "options": [
            {"en": "As much as I always could", "hi": "जितना हमेशा देख पाती थी"},
            {"en": "Not quite so much now", "hi": "अब उतना नहीं"},
            {"en": "Definitely not so much now", "hi": "अब निश्चित रूप से बहुत कम"},
            {"en": "Not at all", "hi": "बिल्कुल नहीं"},
        ],
    },
    {
        "no": 2,
        "reverse_scored": False,
        "text": {
            "en": "I have looked forward with enjoyment to things",
            "hi": "मैं चीज़ों का उत्साह से इंतज़ार करती रही हूँ",
        },
        "options": [
            {"en": "As much as I ever did", "hi": "जितना पहले करती थी"},
            {"en": "Rather less than I used to", "hi": "पहले से थोड़ा कम"},
            {"en": "Definitely less than I used to", "hi": "पहले से निश्चित रूप से कम"},
            {"en": "Hardly at all", "hi": "लगभग बिल्कुल नहीं"},
        ],
    },
    {
        "no": 3,
        "reverse_scored": True,
        "text": {
            "en": "I have blamed myself unnecessarily when things went wrong",
            "hi": "जब कुछ गलत हुआ तो मैंने बिना वजह खुद को दोषी ठहराया",
        },
        "options": [
            {"en": "Yes, most of the time", "hi": "हाँ, अधिकतर समय"},
            {"en": "Yes, some of the time", "hi": "हाँ, कभी-कभी"},
            {"en": "Not very often", "hi": "बहुत कम"},
            {"en": "No, never", "hi": "नहीं, कभी नहीं"},
        ],
    },
    {
        "no": 4,
        "reverse_scored": False,
        "text": {
            "en": "I have been anxious or worried for no good reason",
            "hi": "मैं बिना किसी ठोस वजह के चिंतित या परेशान रही हूँ",
        },
        "options": [
            {"en": "No, not at all", "hi": "नहीं, बिल्कुल नहीं"},
            {"en": "Hardly ever", "hi": "बहुत कम"},
            {"en": "Yes, sometimes", "hi": "हाँ, कभी-कभी"},
            {"en": "Yes, very often", "hi": "हाँ, बहुत बार"},
        ],
    },
    {
        "no": 5,
        "reverse_scored": True,
        "text": {
            "en": "I have felt scared or panicky for no very good reason",
            "hi": "मैं बिना किसी ठोस वजह के डरी हुई या घबराई हुई महसूस करती रही हूँ",
        },
        "options": [
            {"en": "Yes, quite a lot", "hi": "हाँ, काफ़ी ज़्यादा"},
            {"en": "Yes, sometimes", "hi": "हाँ, कभी-कभी"},
            {"en": "No, not much", "hi": "नहीं, ज़्यादा नहीं"},
            {"en": "No, not at all", "hi": "नहीं, बिल्कुल नहीं"},
        ],
    },
    {
        "no": 6,
        "reverse_scored": True,
        "text": {
            "en": "Things have been getting on top of me",
            "hi": "चीज़ें मुझ पर हावी होती जा रही हैं",
        },
        "options": [
            {"en": "Yes, most of the time I haven't been able to cope at all", "hi": "हाँ, अधिकतर समय मैं बिल्कुल सँभाल नहीं पाई"},
            {"en": "Yes, sometimes I haven't been coping as well as usual", "hi": "हाँ, कभी-कभी मैं सामान्य जैसा नहीं सँभाल पाई"},
            {"en": "No, most of the time I have coped quite well", "hi": "नहीं, अधिकतर समय मैंने ठीक से सँभाला"},
            {"en": "No, I have been coping as well as ever", "hi": "नहीं, मैं हमेशा की तरह सँभाल रही हूँ"},
        ],
    },
    {
        "no": 7,
        "reverse_scored": True,
        "text": {
            "en": "I have been so unhappy that I have had difficulty sleeping",
            "hi": "मैं इतनी दुखी रही हूँ कि मुझे सोने में कठिनाई हुई",
        },
        "options": [
            {"en": "Yes, most of the time", "hi": "हाँ, अधिकतर समय"},
            {"en": "Yes, sometimes", "hi": "हाँ, कभी-कभी"},
            {"en": "Not very often", "hi": "बहुत कम"},
            {"en": "No, not at all", "hi": "नहीं, बिल्कुल नहीं"},
        ],
    },
    {
        "no": 8,
        "reverse_scored": True,
        "text": {
            "en": "I have felt sad or miserable",
            "hi": "मैं उदास या दुखी महसूस करती रही हूँ",
        },
        "options": [
            {"en": "Yes, most of the time", "hi": "हाँ, अधिकतर समय"},
            {"en": "Yes, quite often", "hi": "हाँ, काफ़ी बार"},
            {"en": "Not very often", "hi": "बहुत कम"},
            {"en": "No, not at all", "hi": "नहीं, बिल्कुल नहीं"},
        ],
    },
    {
        "no": 9,
        "reverse_scored": True,
        "text": {
            "en": "I have been so unhappy that I have been crying",
            "hi": "मैं इतनी दुखी रही हूँ कि मैं रोती रही हूँ",
        },
        "options": [
            {"en": "Yes, most of the time", "hi": "हाँ, अधिकतर समय"},
            {"en": "Yes, quite often", "hi": "हाँ, काफ़ी बार"},
            {"en": "Only occasionally", "hi": "केवल कभी-कभार"},
            {"en": "No, never", "hi": "नहीं, कभी नहीं"},
        ],
    },
    {
        "no": 10,
        "reverse_scored": True,
        "text": {
            "en": "The thought of harming myself has occurred to me",
            "hi": "खुद को नुकसान पहुँचाने का विचार मेरे मन में आया है",
        },
        "options": [
            {"en": "Yes, quite often", "hi": "हाँ, काफ़ी बार"},
            {"en": "Sometimes", "hi": "कभी-कभी"},
            {"en": "Hardly ever", "hi": "बहुत कम"},
            {"en": "Never", "hi": "कभी नहीं"},
        ],
    },
]

_QUESTION_BY_NO = {q["no"]: q for q in QUESTIONNAIRE}


def score_answer(question_no: int, answer: int) -> int:
    """Convert a chosen option index (0-3, in display order) to its EPDS score.

    Normal-scored items keep the index; reverse-scored items invert it.
    """
    if question_no not in _QUESTION_BY_NO:
        raise ValueError(f"question_no must be 1-{NUM_QUESTIONS}, got {question_no}")
    if answer not in (0, 1, 2, 3):
        raise ValueError(f"answer must be 0-3, got {answer}")
    if question_no in NORMAL_SCORED:
        return answer
    return 3 - answer


def risk_band(total: int) -> str:
    """Map a 0-30 total to a low / medium / high risk band."""
    if total <= LOW_MAX:
        return "low"
    if total <= MEDIUM_MAX:
        return "medium"
    return "high"


def compute(answers: dict[int, int]) -> dict:
    """Score a set of answers.

    ``answers`` maps question_no (1-10) to the chosen option index (0-3).
    Returns per-question scores plus the total, risk band, self-harm flag,
    and whether every question has been answered.
    """
    per_question = {}
    for no, answer in answers.items():
        per_question[no] = score_answer(no, answer)

    complete = len(answers) == NUM_QUESTIONS
    total = sum(per_question.values())
    self_harm_flag = per_question.get(SELF_HARM_QUESTION, 0) > 0

    return {
        "per_question": per_question,
        "total_score": total,
        "max_score": MAX_SCORE,
        "risk_band": risk_band(total) if complete else None,
        "self_harm_flag": self_harm_flag,
        "complete": complete,
        "answered": len(answers),
        "remaining": NUM_QUESTIONS - len(answers),
    }


def questionnaire(language: str | None = None) -> list[dict]:
    """Return the 10 items. With a language, flatten text/options to that
    language (falling back to English); without one, return both languages."""
    if not language:
        return QUESTIONNAIRE

    def pick(d: dict) -> str:
        return d.get(language) or d["en"]

    return [
        {
            "no": q["no"],
            "reverse_scored": q["reverse_scored"],
            "text": pick(q["text"]),
            "options": [pick(o) for o in q["options"]],
        }
        for q in QUESTIONNAIRE
    ]

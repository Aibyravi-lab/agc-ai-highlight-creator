class HighlightService:

    # Gaming moment keywords
    KEYWORD_SCORES = {

        # High impact moments
        "explosion": 10,
        "explode": 10,
        "kill": 9,
        "headshot": 10,
        "victory": 8,
        "boss": 8,
        "crash": 8,
        "accident": 8,
        "jump": 7,
        "fight": 7,
        "battle": 7,

        # Medium moments
        "enemy": 6,
        "attack": 6,
        "speed": 5,
        "race": 5,
        "drift": 5,
        "danger": 5,

        # Low interest moments
        "driving": 2,
        "car": 1,
        "road": 1,
        "snow": 1
    }


    @classmethod
    def analyze_description(cls, description: str):

        description = description.lower()

        score = 0
        matched_keywords = []

        for keyword, value in cls.KEYWORD_SCORES.items():

            if keyword in description:

                score += value
                matched_keywords.append(keyword)


        return {
            "description": description,
            "score": score,
            "keywords_found": matched_keywords,
            "is_highlight": score >= 5
        }
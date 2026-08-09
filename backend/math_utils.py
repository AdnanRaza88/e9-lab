def weighted_total(scores, criteria):
    weight_map = {c["name"]: c["weight"] for c in criteria}
    total = sum(s.score * weight_map[s.name] for s in scores) / 100
    return round(total, 2)


def map_grade(percentage):
    if percentage >= 90:
        return "A"
    if percentage >= 80:
        return "B"
    if percentage >= 70:
        return "C"
    if percentage >= 60:
        return "D"
    return "F"


def detect_disagreements(scores):
    flags = []
    for i in range(len(scores)):
        for j in range(i + 1, len(scores)):
            diff = abs(scores[i].score - scores[j].score)
            if diff > 20:
                flags.append({
                    "criterion_a": scores[i].name,
                    "criterion_b": scores[j].name,
                    "difference": diff
                })
    return flags

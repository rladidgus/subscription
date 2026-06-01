export function rankLabel(rankCode: string) {
  const normalized = String(rankCode).trim();
  if (!normalized) {
    return "순위 미상";
  }
  return `${Number(normalized) || normalized}순위`;
}

export function residenceLabel(resideCode: string) {
  const normalized = String(resideCode).padStart(2, "0");
  switch (normalized) {
    case "01":
      return "해당지역 거주자";
    case "02":
      return "기타지역 거주자";
    default:
      return "거주구분 미상";
  }
}

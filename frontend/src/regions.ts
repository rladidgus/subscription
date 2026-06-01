export const regionOptions = [
  { value: "", label: "전체 지역" },
  { value: "11", label: "서울" },
  { value: "26", label: "부산" },
  { value: "27", label: "대구" },
  { value: "28", label: "인천" },
  { value: "29", label: "광주" },
  { value: "30", label: "대전" },
  { value: "31", label: "울산" },
  { value: "36", label: "세종" },
  { value: "41", label: "경기" },
  { value: "42", label: "강원" },
  { value: "43", label: "충북" },
  { value: "44", label: "충남" },
  { value: "45", label: "전북" },
  { value: "46", label: "전남" },
  { value: "47", label: "경북" },
  { value: "48", label: "경남" },
  { value: "50", label: "제주" },
  { value: "51", label: "강원특별자치도" },
  { value: "52", label: "전북특별자치도" },
];

export function getRegionLabel(regionCode: string) {
  return regionOptions.find((region) => region.value === regionCode)?.label ?? "지역 미상";
}

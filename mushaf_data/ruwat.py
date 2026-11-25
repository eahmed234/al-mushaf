"""The twenty ruwāt of the Shāṭibiyyah and the Durrah, in the order of the qurrāʾ."""

RUWAT = [
    "qalun", "warsh", "bazzi", "qunbul", "duri_abuamr", "susi", "hisham", "ibn_dhakwan",
    "shuba", "hafs", "khalaf_an_hamzah", "khallad", "abul_harith", "duri_kisai",
    "ibn_wardan", "ibn_jammaz", "ruways", "rawh", "ishaq", "idris",
]
SEVEN = RUWAT[:14]  # the Shāṭibiyyah's fourteen

QARI = {
    "nafi": ["qalun", "warsh"], "ibn_kathir": ["bazzi", "qunbul"], "abu_amr": ["duri_abuamr", "susi"],
    "ibn_amir": ["hisham", "ibn_dhakwan"], "asim": ["shuba", "hafs"], "hamzah": ["khalaf_an_hamzah", "khallad"],
    "kisai": ["abul_harith", "duri_kisai"], "abu_jafar": ["ibn_wardan", "ibn_jammaz"], "yaqub": ["ruways", "rawh"],
    "khalaf_ashir": ["ishaq", "idris"],
}

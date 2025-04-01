import random

voor = [
    "je",
    "tu",
    "il",
    "nous",
    "vous",
    "ils",
]

vervoegen = {
    "aller": [
        "aille",
        "ailles",
        "aille",
        "allions",
        "alliez",
        "aillent",
    ],
    "avoir": [
        "aie",
        "aies",
        "ait",
        "ayons",
        "ayez",
        "aient",
    ],
    "être": [
        "sois",
        "sois",
        "soit",
        "soyons",
        "soyez",
        "soient",
    ],
    "savoir": [
        "sache",
        "saches",
        "sache",
        "sachions",
        "sachiez",
        "sachent",
    ],
    "vouloir": [
        "veuille",
        "veuilles",
        "veuille",
        "veuillons",
        "veuilliez",
        "veuillent",
    ],
    "faire": [
        "fasse",
        "fasses",
        "fasse",
        "fassions",
        "fassiez",
        "fassent",
    ],
    "pouvoir": [
        "puisse",
        "puisses",
        "puisse",
        "puissions",
        "puissiez",
        "puissent",
    ],
    "falloir": [
        "faille",
        "failles",
        "faille",
        "faillions",
        "failliez",
        "faillent",
    ],
    "pleuvoir": [
        "pleuve",
        "pleuves",
        "pleuve",
        "pleuvions",
        "pleuviez",
        "pleuvent",
    ],
}

def stel_vraag():

    werkwoorden = ["aller", "avoir", "être", "savoir", "vouloir", 
                   "faire", "pouvoir", "falloir", "pleuvoir"]
    werkwoord = random.choice(werkwoorden)
    persoon = random.randint(0, 5) 
    
    print(f"Vervoeg het werkwoord '{werkwoord}' met '{voor[persoon]}'")
    antwoord = input("Jouw antwoord: ").lower().strip()
    
    correct = vervoegen[werkwoord][persoon]
    if antwoord == correct:
        print("✓ Correct!")
        return True
    else:
        print(f"✗ Helaas, het juiste antwoord is: {correct}")
        return False

def start_quiz():
    score = 0
    aantal_vragen = 100
    
    print("=== Franse Werkwoorden Quiz ===")
    print("Je krijgt 100 vragen over werkwoorden in de subjonctif.")
    print("Typ het juiste vervoegde werkwoord.\n")
    
    for i in range(aantal_vragen):
        print(f"\nVraag {i+1}:")
        if stel_vraag():
            score += 1
            
    print(f"\nJe eindscore: {score}/{aantal_vragen}")
    if score == aantal_vragen:
        print("Perfect! Je kent je werkwoorden goed!")
    elif score >= 3:
        print("Goed gedaan!")
    else:
        print("Blijf oefenen!")

if __name__ == "__main__":
    start_quiz()
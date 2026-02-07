import json

# Input text
text = """
        Characters: 
        Bell Cranel: The protagonist, a young adventurer of Hestia Familia, and the sole possessor of the rare skill "Argonaut."
        Welf Crozzo: A human blacksmith of Hestia Familia, wielding the rare Crozzo magic sword lineage. Specializes in anti-magic weaponry.
        Liliruca Erde (Lily): A Prum strategist and supporter in Hestia Familia, formerly a thief from Soma Familia.
        Haruhime Sanjouno: A Renart capable of using the magic Uchide no Kozuchi, a former member of Ishtar Familia.
        Hestia: The goddess of Hestia Familia, known for her strong bond with Bell.
        Yamato Mikoto: A human warrior from the Far East, originally from Takemikazuchi Familia, now assisting Hestia Familia.
        Ais Wallenstein: A renowned sword princess and top-tier adventurer of Loki Familia, admired by Bell Cranel.
        Ryuu Leon: An elf and former adventurer of the Astraea Familia, currently working at the Hostess of Fertility and an ally of Hestia Familia.
        Freya: The goddess of beauty and leader of Freya Familia, known for her manipulative nature and interest in Bell Cranel.
        Ottar: The strongest adventurer in Orario and captain of Freya Familia, unwaveringly loyal to Freya.
        Finn Deimne: The Prum leader of Loki Familia, known for his strategic mind and leadership skills.
        Riveria Ljos Alf: An elven mage and a high-ranking member of Loki Familia, respected for her wisdom and power.
        Gareth Landrock: A dwarf warrior and one of the executives of Loki Familia, known for his strength and experience.
        Tione Hiryute: An Amazoness and one of the Hiryute sisters in Loki Familia, known for her combat prowess and fiery personality.
        Tiona Hiryute: The younger Hiryute sister, also an Amazoness in Loki Familia, cheerful and equally formidable in battle.
        Lefiya Viridis: An elven mage in Loki Familia, aspiring to become as powerful as her seniors.
        Bete Loga: A werewolf warrior in Loki Familia, known for his speed, strength, and abrasive personality.
        Asfi Al Andromeda: The captain of Hermes Familia, known for her intelligence and invention skills.
        Aisha Belka: A former member of Ishtar Familia, now allied with Hermes Familia, known for her strength and protective nature.
        Takemikazuchi: The god of Takemikazuchi Familia, caring deeply for his followers from the Far East.
        Miach: The god of Miach Familia, known for his gentle nature and healing abilities.
        Nahza Erisuis: A Chienthrope and member of Miach Familia, skilled in potion-making and healing.
        Hephaestus: The goddess of the forge and leader of Hephaestus Familia, renowned for her exceptional blacksmithing skills.
        Soma: The god of Soma Familia, initially indifferent to his followers, known for creating a potent wine.
        Zanis Lustra: A former high-ranking member of Soma Familia, known for his manipulative and ambitious nature.
        Hermes: The god of Hermes Familia, known for his cunning and playful personality, often acting as a messenger among gods.
        Ouranos: The god overseeing the Guild in Orario, maintaining balance between the surface and the Dungeon.
        Fels: An enigmatic mage working under Ouranos, known for their vast knowledge and mysterious past.
        Astraea: The goddess of justice and former leader of Astraea Familia, known for her unwavering sense of righteousness.
        Alise Lovell: The former captain of Astraea Familia, known for her leadership and bravery.
        Gojouno Kaguya: A former member of Astraea Familia, known for her strict demeanor and swordsmanship.
        Lyra: A former member of Astraea Familia, known for her agility and combat skills.
        Mia Grand: The Dwarven owner and head chef of the Hostess of Fertility, known for her strict demeanor and exceptional cooking.
        Syr Flova: A kind and cheerful waitress, secretly a persona of Freya
        Anya Fromel: A cat person and energetic waitress, known for her cheerful personality and strength. Sister of Allen, she previously belonged to Freya Familia.
        Chloe Rollo: A cat person and waitress with a mischievous streak.
        Runoa Faust: A human waitress who often teases customers and coworkers.
        Allen Fromel: An Arachne and twin brother of Anya, a cold and ruthless member of Freya Familia.
        Hedin Selland: An Elf with outstanding swordsmanship, devoted to Freya.
        Hegni Ragnar: A Dark-Elf mage and swordsman, among Freya's strongest warriors.
        Eina Tulle: A half-elf receptionist at the Guild, serving as Bell's advisor, known for her caring and responsible nature.
        Misha Flott: A human receptionist at the Guild, colleague and friend of Eina.
        Royman Mardeel: The highest-ranking Guild official, often focused on maintaining order.
        Loki: The mischievous and cunning goddess of Loki Familia, known for her playful nature and sharp intellect.
        Ganesha: The flamboyant and boisterous god of Ganesha Familia, known for his self-proclaimed title as the "God of the Masses" and his passion for maintaining public order.
        Shakti Varma: The human captain of Ganesha Familia, known for her commanding presence and strong sense of justice.
        Brin: One of Freya Familia's elite adventurers, part of the infamous Prum quartet.
        Hegni: Known for their impressive teamwork and unwavering loyalty to Freya.
        Alfrigg: Among the elite tier of Freya Familia, specializes in close-quarter combat.
        Dvalinn: Another member of the Prum quartet, skilled in supporting the familia's tactical operations.

        Locations:
        Orario: The Labyrinth City, built atop the Dungeon, serving as a hub for adventurers and familias.
        Dungeon: A vast, multi-leveled labyrinth beneath Orario, filled with monsters, treasures, and mysteries.
        Hostess of Fertility: A popular tavern in Orario, known for its delicious food and secretive, capable staff.
        Guild: The organization responsible for managing adventurers and maintaining order in Orario, headquartered near the Dungeon entrance.
        Tower of Babel: A towering structure in the center of Orario, serving as the Dungeon's entrance and housing various shops.
        Daedalus Street: A chaotic, maze-like district in Orario, known for its hidden passages and connection to the Knossos.
        Knossos: A secret labyrinth built by Daedalus, paralleling the Dungeon and used by Evilus for their operations.
        Under Resort: Freya Familia's secret base beneath Orario, a luxurious and secure stronghold.
        Rakia: A militant nation frequently at odds with Orario, known for its attempts to seize control of the Dungeon.
        Far East: A distant region characterized by its unique culture and traditions, home to Yamato Mikoto and Takemikazuchi Familia.
        Rivira: A settlement on the 18th floor of the Dungeon, often used as a rest point.

        Organizations:
        Hestia Familia: A small yet growing familia led by the goddess Hestia, known for its close-knit members and rapid rise in strength.
        Loki Familia: One of the most powerful familias in Orario, led by the goddess Loki, boasting numerous top-tier adventurers.
        Freya Familia: A formidable familia led by the goddess Freya, known for its strength and the unwavering loyalty of its members.
        Takemikazuchi Familia: A familia of Far Eastern origin, led by the god Takemikazuchi, known for their martial arts prowess.
        Miach Familia: A small familia led by the god Miach, specializing in healing and potion-making.
        Hephaestus Familia: Renowned for their blacksmithing skills, this familia is led by the goddess Hephaestus and produces high-quality weapons and armor.
        Soma Familia: Led by the god Soma, this familia was once troubled due to the addictive wine Soma produced but has since reformed.
        Hermes Familia: A familia known for their information-gathering and diverse skills, led by the god Hermes.
        Astraea Familia: Formerly led by the goddess Astraea, this familia was dedicated to justice and maintaining peace in Orario.
        Evilus: A criminal organization seeking to disrupt Orario, often clashing with the Guild and prominent familias.
        Ikelos Familia: A notorious familia involved in illegal activities, known for trafficking Xenos and other crimes.

        Terminology:
        Adventurer: Individuals who explore the Dungeon, battling monsters and collecting treasures.
        Alias: A title given to adventurers upon reaching Level 2, decided by the Gods in Denatus.
        Arcanum: Divine power possessed by Gods, forbidden for use in the mortal realm.
        Charm: A supernatural ability possessed by certain deities to influence others.
        Denatus: A quarterly meeting of Gods to discuss matters like assigning aliases to adventurers.
        Familia: Organizations led by a God or Goddess, consisting of adventurers and supporters.
        Falna: A divine blessing from a deity, enabling adventurers to gain strength and skills.
        Magic: Supernatural abilities or spells acquired by adventurers through their Falna.
        Magic Sword: Weapons capable of casting magic, often at the cost of durability.
        Monsters: Creatures born from the Dungeon, serving as adversaries to adventurers.
        Skills: Unique abilities adventurers discover through their Falna that enhance their capabilities.
        Status: A quantified system tracking an adventurer's parameters like strength and agility.
        War Game: A structured battle between Familias to settle disputes or gain influence.
        Xenos: Monsters with human intelligence, seeking coexistence with humans.
        Three Great Quests: Legendary missions involving the defeat of Behemoth, Leviathan, and the One-Eyed Black Dragon.
        Expedition: A large-scale Dungeon exploration undertaken by high-level adventurers.
        """

# Function to process the input into nested JSON
def parse_text_to_json(input_text):
    result = {}
    current_section = None
    
    for line in input_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.endswith(":") and not line.startswith(" "):  # Indicates a section header
            current_section = line[:-1]  # Remove trailing colon
            result[current_section] = {}
        elif current_section:
            key, _, value = line.partition(":")
            if key and value:
                result[current_section][key.strip()] = value.strip()
    
    return result

# Parse text into JSON
parsed_data = parse_text_to_json(text)

# File path
file_path = "refining_glossary.json"

# Load existing data or initialize an empty dictionary if the file is empty/invalid
try:
    with open(file_path, "r") as file:
        try:
            existing_data = json.load(file)
        except json.JSONDecodeError:
            existing_data = {}  # Handle invalid JSON
except FileNotFoundError:
    existing_data = {}

# Merge existing data with new data
existing_data.update(parsed_data)

# Save updated JSON to file
with open(file_path, "w") as file:
    json.dump(existing_data, file, indent=4)

print(f"Data successfully saved to {file_path}.")
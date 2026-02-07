import time
import json
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
gemini_key = os.environ["GEMINI_KEY"]
MODEL = "gemini-2.5-flash-preview-05-20"

SYSTEM_MSG = (
    "You are a senior localisation editor creating a concise **style guide** for translators. "
    "Analyse the provided excerpts and output STRICTLY valid JSON with the following keys:\n"
    "{"
    '"voice",        # e.g. "close third-person, lightly omniscient"\n'
    '"tone",         # 3-5 adjectives (comma-separated)\n'
    '"sentence_span",# typical sentence length in English words (e.g. "14-22")\n'
    '"pacing_notes", # how narration accelerates or pauses\n'
    '"punctuation",  # rules for ellipses, em-dashes, quotes, italics\n'
    '"dialogue",     # formatting + how much tag variety\n'
    '"idiom_guidance",# any recurring Japanese/Chinese idioms & how to render them\n'
    '"onomatopoeia", # keep kana? replace with English SFX? give examples\n'
    '"honorifics",   # keep -san / drop / footnote\n'
    '"register_switch", # how characters’ speech levels shift\n'
    '"dos",          # list of 5 translator DOs\n'
    '"donts"         # list of 5 translator DON’Ts\n'
    "}"
    "Your response must be a JSON object and nothing else. Do not use any markdown, or you will break the automation."
)

def generate_style_profile(passages):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel(model_name=MODEL,
                                  system_instruction=SYSTEM_MSG)

    prompt = build_prompt(passages)

    for attempt in range(5):
        try:
            resp = model.generate_content(prompt)
            payload = resp.candidates[0].content.parts[0].text.strip()
            style_json = json.loads(payload)        # validate
            return style_json
        except Exception as err:
            if attempt == 4:
                raise
            time.sleep(8)

passages = [
    """
    After I reject her, she looks down and then starts running, leaving me behind.
    I almost chase after her, but in the end, I don't budge from the spot.
    Asking her to stop and wait after I just rejected her confession would be illogical, cruel, and contradictory. I can hear a voice in my head yelling that I have no right.
    A rumble tears through the sky, as if the heavens are sobbing.
    Rain begins to fall.
    Even as the raindrops pelt me, I can't bring myself to take a single step. Who knows how much time passes while I stand still.
    “…Lyu…Aiz…I have to…”
    With that delirious murmur, I finally leave behind that memorystrewn park.
    My entire body is soaked, on the verge of just melting away in the rain as I struggle to drag myself forward.
    I finally reach the place where I last saw my friends. They were holding off Freya Familia in the second district, meaning we were in the northeast quadrant of the city.
    Asfi calls out and says, “Bell Cranell! Looks like you're safe after all. I was concerned, since we couldn't delay Vana Freya and the rest for very long…”
    “Sorry…everyone was injured, so we couldn't follow after you…” Aiz murmurs apologetically.
    """,
    """
    The truth is that I'm desperate. Looking at those golden eyes of hers is the last thing I want to do right now. I don't want to feel her touch. Not by the person I look up to.
    Not after I so thoughtlessly hurt someone precious to me because all my attention is focused on another. Aiz opens her eyes a little wider, clearly shocked by my reaction.
    When I think about how none of this is her fault, I just want to curl up and die in a hole somewhere.
    “Bell…”
    Lady Hestia stares at me, but she doesn't say anything else. I guess as someone who possesses the foresight of a goddess, she can see right through me. I'm sure she already understands everything.
    “…To some extent or another, everyone's hurt. Let's head inside before anyone gets sick from being out in this rain.”
    Lord Hermes doesn't broach the unspoken topic on everyone's mind. Following his proposal, we carry the injured inside, leaving the rainy streets behind.
    —Those are my memories of yesterday.
    “………”
    The morning of the third day of the Goddess Festival has arrived. Today, there's no rain falling like tears, but dark gray clouds still fill the sky.
    I stare out at the hanging wall of gray from a corridor of Hearthstone Manor without really looking at anything. After we carried the injured to The Benevolent Mistress to let them recover, we went back to our home.
    """,
    """
    As the battle cries make the very air tremble, I'm forced to join the other warriors and become one of them.
    A thrusting sword point, a spinning kick that almost touches the ground, an unmistakable murderous glint in his eyes—this is anything but training or practice. Van's momentum is overwhelming.
    Meanwhile, I'm just barely managing to stay alive. The unease I felt when I discovered how perfectly these unfamiliar weapons fit in my hands…that's all gone now. 
    I swing again and again, digging in with my feet as I fight desperately. Van isn't someone I can hold back against. A moment of indecision is unthinkable. If I don't fight back with everything I have, I'll be killed!
    “Ya!”
    “Haaaaaaaaah!”
    It's the same for everyone around me. I notice two humans, a man and woman, crossing blades next to me. 
    A dwarf behind me sends an elf flying with a heavy hammer blow, while a beast person and an Amazon are locking blades at close range. 
    If there were a bird flying above the field, it would see a scene of chaotic battle. There are even magic and curses flying through the air as people who should have been comrades in the same familia do their best to kill each other.
    Blood splatters the ground. Some collapse. Weapons fall from slack hands. But then someone picks up a dropped spear or pulls out a bloody sword, stands back up, and returns to the fight.
    The cacophony of sound makes me go pale.
    This is—
    I underestimated this.
    I had no idea.
    I thought they meant it metaphorically when they said they fought to the death. But there's nothing figurative about this vicious combat!
    This is—Folkvangr!
    """,
    """
    “Don't get distracted!”
    “Ghhhh?!”
    Van's furious shout pounds my head, calling me back from my idle thoughts.
    My battle clothes are torn to ribbons by his unending slashes, and when I try frantically to put some distance between us, he follows up with a thrust that threatens to run me through.
    I have no choice.
    My left hand shoots forward.
    “Firebolt!”
    “Guh?!”
    Fire and lightning erupt from my hand, slamming into Van. I used my magic. No, I was forced to use it!
    It's one thing to aim that spell at a monster, but to use it against another adventurer, not as a threat but fully intending to hurt them… that never happened even in all my training with Aiz!
    Van's stomach and chest are scorched and smoking as he staggers. But his eyes just bulge as he glares at me before resuming his assault.
    What unbelievable durability. And the level of technique and skill are plain to see. These fighters are far stronger compared to adventurers of the same level in other familias.
    I can't believe that the people here aren't even considered the core members of Freya Familia!
    “Guaaaaaaaaaaaa?!”
    Screams clearly mark the moment another person gets knocked out of the fight. The adventurers who lost their original opponents immediately leap to their next fight.
    Tens, hundreds, thousands of blades cross on all sides, the sounds melting into the background in the blink of an eye.
    Time feels compressed here. Blood pulses through my body, driven by a desperation to stay alive as I exert every part of my body. 
    This battle royale is nothing like the consecutive battles I've experienced in the Dungeon. With no other choice, I throw myself into the fray.
    """,
    """
    “Welcome, Bell. Thank you for coming.”
    I've been taken from the enormous hall and brought to the goddess' chamber, where Lady Freya greets me. I'm startled to see the goddess of beauty herself meet me at the door and take me by the hand.
    Her skin is smooth as silk, and my heart races at the soft warmth it gives off as she leads me to the center of the room.
    She sits on her couch while I sit on the armchair next to the round table.
    “You look pale. Did you have a particularly harsh baptism?”
    “…Yes. On the field, Master…Hedin and the others…put me through my paces…”
    “Ahh. I'm sorry for calling for you when you must be so tired.”
    We're alone in her room again tonight. The goddess' chamber is lit in a fantastical light by the moon shining in through the wall-sized window.
    Even now, I still can't really believe that the famed goddess of beauty herself is here before my eyes. It's just too unreal. 
    Feeling an exhaustion that can't be ignored and fully understanding how improper it is…I probe her with questions once again, still unable to accept that my memories are false.
    “It's hard to believe I went through such a fearsome battle every day… Today was scary and exhausting.”
    “Ha-ha, that's fair. I suppose the baptism might be a bit unpleasant if you've lost your memories.”
    “………”
    She easily evades the question.
    My mouth twists slightly into an awkward expression, and I quickly give up. I'm far too badly outclassed to be trying to probe a goddess for inconsistencies.
    """,
    """
    The moon was pretty.
    Sadly, there was no one beside her who could share in that thought. Beneath the clear night sky that was the opposite of her clouded heart, Hestia was walking along the backstreets of Orario.
    She was all alone after having forcibly persuaded Lilly and the others who had tried to stop her.

    …I'm being watched…
    
    She did not have the knowledge and experience of an adventurer like Bell, but Hestia still knew that she was being watched by Freya Familia. Or more exactly, the watcher was making their presence known as a warning to her.
    As expected, they fully intended to keep her under watch around the clock.

    Should I try some other time…? No, it was always going to be a given that they know my every move. I have to act and just accept that they will find out! The worst thing I could do is turtle up and become afraid to do anything!
    
    She shook her head and clenched her fists. She had gone out on her own at night for several nights in a row, searching for any gap in Freya's charm.
    Bell was still exposed and isolated. She could not allow herself to just do as Freya wanted while knowing that. Even if that meant acting like she did not know Bell to his face.
    Steeling her resolve again, she took the main route, not the back door that the fool had passed. She did not care if it was reported to Freya and dared them to stop her if they could, even though she knew it would take them less than three seconds to do so.
    Visiting so late at night, she spoke with a visibly annoyed Guild member before finally getting them to pass a message for her and being allowed through.
    Her destination was beneath Guild Headquarters—the Chamber of Prayers.
    “Hestia. So you resisted Freya's charm.”
    “…! You too, Ouranos…?!”
    Hestia leaned in excitedly when she heard him refer to the charm from his seat at the altar. 
    She had clung to the thread of hope that if it was him, if it was the great god who was Orario's creator, but her eyes were on the verge of tears from the emotion of having her hopes confirmed.
    She was a little bit suspicious seeing that the old god made no effort to open his eyes, but she still began to discuss the next moves.
    “Ouranos, I have a letter from Hermes. About how to deal with Freya—”
    “You mustn't.”
    """,
    """
    That was when Bell realized it. It must have been Hestia who had undone the charm afflicting the whole city, and she had always been trying to rescue him.
    His eyes watered at the warmth of her hug, and he started to sniffle, too. His face became as much of a mess as hers as he looked into her eyes and smiled from the depths of his heart.
    “Thank you so much, Goddess!…I love you!”
    “…Yeah, I love you, too!”
    The follower and the goddess shared both tears and smiles. Hugging one more time, they both stood up together. They turned their gazes to the goddess of beauty, who was watching with a grim look.
    “And with that, Freya! I will be taking my Bell back! Not yours! Mine! My beloved Bell with whom I have the deepest bond of anyone and with whom I share a mutual love!”
    “G-Goddess…”
    Bell looked forward and broke into a cold sweat as Hestia decided there of all places to assert her supremacy. The empress, who had just had mud thrown in her face, looked clearly displeased.
    She did not do something so clichéd as bite her nails, but she twirled her hair as she stared at Hestia and Bell holding hands.
    “Unleashing your divine might to the full limit… using ichor and flames, you summoned your temple from the heavens… no, recreated it. So you still had a move to make, Hestia.”
    """
]

def build_prompt(passages: list[str]) -> str:
    joined = "\n---\n".join(p.strip() for p in passages)
    return (
        "Analyse the style of these official English excerpts and fill the JSON template. "
        "Do **not** recap plot. Do **not** add keys. Keep values concise but specific.\n\n"
        f"{joined}"
    )

profile = generate_style_profile(passages)
print(json.dumps(profile, indent=2, ensure_ascii=False))
with open("style_profile.json", "w", encoding="utf-8") as f:
    json.dump(profile, f, indent=2, ensure_ascii=False)
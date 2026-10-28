# Transcriptions des scénarios (test automatisé)

## S1 / variante 1 — ✅ réussi — Réserver un indien bon marché au centre, 4 pers., vendredi 19h

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : I want a cheap indian restaurant in the centre
- **BOT** : I found 3 matching restaurants. I'd suggest Kohinoor, a cheap indian restaurant in the centre. Would you like me to book a table, or shall I give you more details?
- **USER** : Book it for 4 people on friday at 7pm
- **BOT** : Sure, let's book Kohinoor. Your booking is confirmed: Kohinoor, 4 people, Friday at 19:00. Reference number: A8DB129B. Anything else I can do for you?

*Résultat : réservé kohinoor (4 pers., friday 19:00)*

## S1 / variante 2 — ✅ réussi — Réserver un indien bon marché au centre, 4 pers., vendredi 19h

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : hi, can you find me an inexpensive Indian place in the city centre?
- **BOT** : I found 3 matching restaurants. I'd suggest Kohinoor, a cheap indian restaurant in the centre. Would you like me to book a table, or shall I give you more details?
- **USER** : yes please
- **BOT** : Sure, let's book Kohinoor. How many people should I book for?
- **USER** : 4 people, friday, 19:00
- **BOT** : All set! I've booked a table at Kohinoor for 4 people on Friday at 19:00. Your reference number is A8DB129B. Is there anything else I can help you with?

*Résultat : réservé kohinoor (4 pers., friday 19:00)*

## S2 / variante 1 — ✅ réussi — Trouver un italien dans le nord + adresse et téléphone (sans réserver)

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : Looking for an italian restaurant in the north
- **BOT** : How about Da Vinci Pizzeria? It is a cheap italian restaurant in the north. Shall I book it for you?
- **USER** : What is the address and phone number?
- **BOT** : For Da Vinci Pizzeria, the address is 20 Milton Road Chesterton and the phone number is 01223351707. Would you like me to book a table?

*Résultat : adresse+téléphone d'un italien du nord donnés*

## S2 / variante 2 — ✅ réussi — Trouver un italien dans le nord + adresse et téléphone (sans réserver)

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : I'd like some Italian food, north part of town
- **BOT** : I'd suggest Da Vinci Pizzeria, a cheap italian restaurant in the north. Would you like me to book a table, or shall I give you more details?
- **USER** : can I get the phone number please
- **BOT** : For Da Vinci Pizzeria, the phone number is 01223351707. Would you like me to book a table?
- **USER** : and the address too
- **BOT** : For Da Vinci Pizzeria, the address is 20 Milton Road Chesterton. Would you like me to book a table?

*Résultat : adresse+téléphone d'un italien du nord donnés*

## S3 / variante 1 — ✅ réussi — Réserver un britannique cher, 2 pers., samedi 20h (demander un autre si besoin)

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : I need an expensive british restaurant
- **BOT** : I found 6 matching restaurants. I'd suggest Fitzbillies Restaurant, an expensive british restaurant in the centre. Would you like me to book a table, or shall I give you more details?
- **USER** : do you have another one?
- **BOT** : Another option is Graffiti, an expensive british restaurant in the west. Would you like to book it?
- **USER** : Book a table for 2 on saturday at 8pm
- **BOT** : Sure, let's book Graffiti. All set! I've booked a table at Graffiti for 2 people on Saturday at 20:00. Your reference number is 843F5883. Is there anything else I can help you with?

*Résultat : réservé graffiti (2 pers., saturday 20:00)*

## S3 / variante 2 — ✅ réussi — Réserver un britannique cher, 2 pers., samedi 20h (demander un autre si besoin)

- **BOT** : Hi there! Tell me what you feel like eating (cuisine, area or price range) and I'll find you a restaurant.
- **USER** : expensive british food please
- **BOT** : I found 6 matching restaurants. How about Fitzbillies Restaurant? It is an expensive british restaurant in the centre. Shall I book it for you?
- **USER** : Book it for 2 people on Saturday at 20:00
- **BOT** : Sure, let's book Fitzbillies Restaurant. All set! I've booked a table at Fitzbillies Restaurant for 2 people on Saturday at 20:00. Your reference number is A7BFE3A8. Is there anything else I can help you with?

*Résultat : réservé fitzbillies restaurant (2 pers., saturday 20:00)*

## S4 / variante 1 — ✅ réussi — Végétarien (inexistant) puis alternative, 3 pers., dimanche 12h30

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : I'm looking for a vegetarian restaurant
- **BOT** : Sorry, I couldn't find any vegetarian restaurants. I can help with cuisines such as african, asian oriental, british, chinese, european, french, gastropub, indian. Which one would you like?
- **USER** : ok then an italian restaurant is fine
- **BOT** : Okay, I'm looking for italian restaurants. Do you have a preferred area? (north, south, east, west or centre)
- **USER** : Book a table for 3 on sunday at 12:30
- **BOT** : I'd suggest Ask Restaurant, a cheap italian restaurant in the centre. Let's book it. Your booking is confirmed: Ask Restaurant, 3 people, Sunday at 12:30. Reference number: D219DB72. Anything else I can do for you?

*Résultat : réservation ask restaurant*

## S4 / variante 2 — ✅ réussi — Végétarien (inexistant) puis alternative, 3 pers., dimanche 12h30

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : Do you have vegetarian food?
- **BOT** : Sorry, I couldn't find any vegetarian restaurants. I can help with cuisines such as african, asian oriental, british, chinese, european, french, gastropub, indian. Which one would you like?
- **USER** : chinese then
- **BOT** : Okay, I'm looking for chinese restaurants. Do you have a preferred area? (north, south, east, west or centre)
- **USER** : reserve for 3 people sunday 12:30 please
- **BOT** : I'd suggest Charlie Chan, a cheap chinese restaurant in the centre. Let's book it. All set! I've booked a table at Charlie Chan for 3 people on Sunday at 12:30. Your reference number is B58084DF. Is there anything else I can help you with?

*Résultat : réservation charlie chan*

## S5 / variante 1 — ✅ réussi — Chinois, aucune préférence prix/zone, 6 pers., jeudi 18h

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : I want chinese food, I don't care about the price or the area
- **BOT** : I found 17 matching restaurants. How about Charlie Chan? It is a cheap chinese restaurant in the centre. Shall I book it for you?
- **USER** : Book a table for 6 people on thursday at 6pm
- **BOT** : Sure, let's book Charlie Chan. All set! I've booked a table at Charlie Chan for 6 people on Thursday at 18:00. Your reference number is 0231E674. Is there anything else I can help you with?

*Résultat : réservé charlie chan (6 pers., thursday 18:00)*

## S5 / variante 2 — ✅ réussi — Chinois, aucune préférence prix/zone, 6 pers., jeudi 18h

- **BOT** : Hi there! Tell me what you feel like eating (cuisine, area or price range) and I'll find you a restaurant.
- **USER** : chinese restaurant please, any price, any area
- **BOT** : I found 17 matching restaurants. How about Charlie Chan? It is a cheap chinese restaurant in the centre. Shall I book it for you?
- **USER** : 6 people thursday 18:00
- **BOT** : Sure, let's book Charlie Chan. Your booking is confirmed: Charlie Chan, 6 people, Thursday at 18:00. Reference number: 0231E674. Anything else I can do for you?

*Résultat : réservé charlie chan (6 pers., thursday 18:00)*

## S6 / variante 1 — ✅ réussi — Modéré à l'est, changer pour l'ouest, 2 pers., lundi 13h

- **BOT** : Hello! I can help you find a restaurant in Cambridge and book a table. What kind of food are you looking for?
- **USER** : hello
- **BOT** : Hi there! Tell me what you feel like eating (cuisine, area or price range) and I'll find you a restaurant.
- **USER** : I'm looking for a moderately priced restaurant in the east
- **BOT** : I found 3 matching restaurants. I'd suggest Curry Prince, a moderately priced indian restaurant in the east. Would you like me to book a table, or shall I give you more details?
- **USER** : actually, I would prefer the west
- **BOT** : I found 3 matching restaurants. How about Meghna? It is a moderately priced indian restaurant in the west. Shall I book it for you?
- **USER** : Book for 2 people on monday at 13:00
- **BOT** : Sure, let's book Meghna. All set! I've booked a table at Meghna for 2 people on Monday at 13:00. Your reference number is 1EE5B394. Is there anything else I can help you with?

*Résultat : réservé meghna (2 pers., monday 13:00)*

## S6 / variante 2 — ✅ réussi — Modéré à l'est, changer pour l'ouest, 2 pers., lundi 13h

- **BOT** : Hi there! Tell me what you feel like eating (cuisine, area or price range) and I'll find you a restaurant.
- **USER** : Hi there
- **BOT** : Hi there! Tell me what you feel like eating (cuisine, area or price range) and I'll find you a restaurant.
- **USER** : moderate price, east side please
- **BOT** : I found 3 matching restaurants. I'd suggest Curry Prince, a moderately priced indian restaurant in the east. Would you like me to book a table, or shall I give you more details?
- **USER** : no wait, make it the west part of town
- **BOT** : I found 3 matching restaurants. I'd suggest Meghna, a moderately priced indian restaurant in the west. Would you like me to book a table, or shall I give you more details?
- **USER** : book a table for two on monday at 1pm
- **BOT** : Sure, let's book Meghna. All set! I've booked a table at Meghna for 2 people on Monday at 13:00. Your reference number is 1EE5B394. Is there anything else I can help you with?

*Résultat : réservé meghna (2 pers., monday 13:00)*

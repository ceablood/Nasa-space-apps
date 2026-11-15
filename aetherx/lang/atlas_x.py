# -*- coding: utf-8 -*-
"""Atlas metinleri: İngilizce kaynak -> (Français, Español, Русский)."""

T = {
    "Sun": ("Soleil", "Sol", "Солнце"),
    "G2V yellow dwarf star": ("Naine jaune de type G2V", "Enana amarilla de tipo G2V", "Жёлтый карлик класса G2V"),
    "15 million °C": ("15 millions de °C", "15 millones de °C", "15 млн °C"),
    "4.6 billion years": ("4,6 milliards d'années", "4.600 millones de años", "4,6 млрд лет"),
    "The Sun is a G-type star at the centre of the Solar System and holds 99.86% of the system's total mass. Every second its core fuses about 600 million tonnes of hydrogen into helium; the energy released lights and warms every planet. Its light takes about 8 minutes 20 seconds to reach Earth.": (
        "Le Soleil est une étoile de type G située au centre du Système solaire ; il concentre 99,86 % de la masse totale du système. Chaque seconde, son cœur transforme environ 600 millions de tonnes d'hydrogène en hélium, et l'énergie libérée éclaire et réchauffe toutes les planètes. Sa lumière met environ 8 minutes et 20 secondes pour atteindre la Terre.",
        "El Sol es una estrella de tipo G situada en el centro del Sistema Solar y reúne el 99,86 % de su masa total. Cada segundo, su núcleo fusiona unos 600 millones de toneladas de hidrógeno en helio; la energía liberada ilumina y calienta todos los planetas. Su luz tarda unos 8 minutos y 20 segundos en llegar a la Tierra.",
        "Солнце — звезда спектрального класса G в центре Солнечной системы; на него приходится 99,86 % всей массы системы. Каждую секунду в его ядре около 600 млн тонн водорода превращается в гелий, и высвобождаемая энергия освещает и согревает все планеты. Свет Солнца доходит до Земли примерно за 8 минут 20 секунд."),
    "Mercury": ("Mercure", "Mercurio", "Меркурий"),
    "−180 to 430 °C": ("de −180 à 430 °C", "de −180 a 430 °C", "от −180 до 430 °C"),
    "The smallest planet and the closest to the Sun. With almost no atmosphere, it heats to 430 °C by day and cools to −180 °C at night. Its surface is cratered like the Moon; the 1,550 km wide Caloris Basin is its largest impact scar.": (
        "La plus petite planète et la plus proche du Soleil. Presque dépourvue d'atmosphère, elle chauffe jusqu'à 430 °C le jour et se refroidit à −180 °C la nuit. Sa surface est criblée de cratères comme celle de la Lune ; le bassin Caloris, large de 1 550 km, est sa plus grande cicatrice d'impact.",
        "El planeta más pequeño y el más cercano al Sol. Casi sin atmósfera, alcanza 430 °C de día y se enfría hasta −180 °C de noche. Su superficie está llena de cráteres como la de la Luna; la cuenca Caloris, de 1.550 km de ancho, es su mayor cicatriz de impacto.",
        "Самая маленькая планета, ближайшая к Солнцу. Почти лишённая атмосферы, днём она раскаляется до 430 °C, а ночью остывает до −180 °C. Её поверхность, как и лунная, покрыта кратерами; крупнейший след удара — равнина Жары шириной 1 550 км."),
    "Venus": ("Vénus", "Venus", "Венера"),
    "Often called Earth's twin in size, but its dense carbon dioxide atmosphere drives a runaway greenhouse effect: at 465 °C it is the hottest planet in the Solar System. Surface pressure is 92 times that of Earth. It spins backwards and very slowly, so its day is longer than its year.": (
        "Souvent qualifiée de jumelle de la Terre par sa taille, elle subit pourtant, sous son épaisse atmosphère de dioxyde de carbone, un effet de serre emballé : avec 465 °C, c'est la planète la plus chaude du Système solaire. La pression au sol vaut 92 fois celle de la Terre. Elle tourne à rebours et très lentement, si bien que son jour dure plus longtemps que son année.",
        "A menudo se la llama gemela de la Tierra por su tamaño, pero su densa atmósfera de dióxido de carbono provoca un efecto invernadero desbocado: con 465 °C es el planeta más caliente del Sistema Solar. La presión en superficie es 92 veces la terrestre. Gira al revés y muy despacio, de modo que su día dura más que su año.",
        "Её часто называют близнецом Земли по размеру, однако плотная атмосфера из углекислого газа вызывает неуправляемый парниковый эффект: при 465 °C это самая горячая планета Солнечной системы. Давление у поверхности в 92 раза выше земного. Она вращается в обратную сторону и очень медленно, поэтому её сутки длиннее года."),
    "Earth": ("Terre", "Tierra", "Земля"),
    "23 h 56 min": ("23 h 56 min", "23 h 56 min", "23 ч 56 мин"),
    "1 natural, thousands artificial": ("1 naturel, des milliers artificiels", "1 natural, miles artificiales", "1 естественный, тысячи искусственных"),
    "The only planet known to have liquid water on its surface and life. Oceans cover 71% of it; its nitrogen-oxygen atmosphere and magnetic field shield living things from harmful radiation. Besides its one natural moon, thousands of artificial satellites orbit it.": (
        "La seule planète connue à posséder de l'eau liquide en surface et la vie. Les océans couvrent 71 % de sa surface ; son atmosphère d'azote et d'oxygène et son champ magnétique protègent les êtres vivants des rayonnements nocifs. Outre son unique satellite naturel, des milliers de satellites artificiels gravitent autour d'elle.",
        "El único planeta conocido con agua líquida en su superficie y con vida. Los océanos cubren el 71 % de su superficie; su atmósfera de nitrógeno y oxígeno y su campo magnético protegen a los seres vivos de la radiación dañina. Además de su única luna natural, la orbitan miles de satélites artificiales.",
        "Единственная известная планета с жидкой водой на поверхности и жизнью. Океаны покрывают 71 % её поверхности; азотно-кислородная атмосфера и магнитное поле защищают живые существа от вредного излучения. Помимо единственного естественного спутника, вокруг неё обращаются тысячи искусственных."),
    "ISS": ("ISS", "EEI", "МКС"),
    "The International Space Station. At about 420 km altitude it travels at 27,600 km/h and circles Earth every 93 minutes; it has been continuously crewed since 2000.": (
        "La Station spatiale internationale. À environ 420 km d'altitude, elle file à 27 600 km/h et fait le tour de la Terre en 93 minutes ; elle est occupée en permanence depuis 2000.",
        "La Estación Espacial Internacional. A unos 420 km de altitud viaja a 27.600 km/h y da una vuelta a la Tierra cada 93 minutos; está habitada de forma continua desde 2000.",
        "Международная космическая станция. На высоте около 420 км она движется со скоростью 27 600 км/ч и облетает Землю за 93 минуты; экипаж находится на ней непрерывно с 2000 года."),
    "Hubble": ("Hubble", "Hubble", "Хаббл"),
    "The Hubble Space Telescope. It has observed the universe from above the atmosphere since 1990.": (
        "Le télescope spatial Hubble. Il observe l'Univers au-dessus de l'atmosphère depuis 1990.",
        "El telescopio espacial Hubble. Observa el universo desde fuera de la atmósfera desde 1990.",
        "Космический телескоп «Хаббл». С 1990 года он наблюдает Вселенную из-за пределов атмосферы."),
    "İMECE": ("İMECE", "İMECE", "İMECE"),
    "Türkiye's domestically built Earth-observation satellite (2023). It flies a Sun-synchronous polar orbit, so it images each region at the same local time.": (
        "Satellite d'observation de la Terre conçu et construit en Turquie (2023). Placé sur une orbite polaire héliosynchrone, il photographie chaque région à la même heure locale.",
        "Satélite de observación de la Tierra de fabricación turca (2023). Sigue una órbita polar heliosíncrona, por lo que fotografía cada región a la misma hora local.",
        "Спутник наблюдения Земли турецкой разработки (2023). Он летает по солнечно-синхронной полярной орбите и снимает каждый район в одно и то же местное время."),
    "GPS satellites": ("Satellites GPS", "Satélites GPS", "Спутники GPS"),
    "Navigation satellites. At 20,200 km altitude they circle Earth twice a day; your phone works out its position from the signals of at least four of them.": (
        "Satellites de navigation. À 20 200 km d'altitude, ils font deux fois par jour le tour de la Terre ; votre téléphone calcule sa position à partir des signaux d'au moins quatre d'entre eux.",
        "Satélites de navegación. A 20.200 km de altitud dan dos vueltas diarias a la Tierra; tu teléfono calcula su posición a partir de las señales de al menos cuatro de ellos.",
        "Навигационные спутники. На высоте 20 200 км они облетают Землю дважды в сутки; ваш телефон определяет своё положение по сигналам как минимум четырёх из них."),
    "Türksat 6A": ("Türksat 6A", "Türksat 6A", "Türksat 6A"),
    "Türkiye's first domestically built communications satellite (2024). In geostationary orbit at 35,786 km it turns at the same rate as Earth, so it stays fixed at one point in the sky.": (
        "Premier satellite de télécommunications construit en Turquie (2024). Sur l'orbite géostationnaire, à 35 786 km, il tourne au même rythme que la Terre et reste donc immobile en un point du ciel.",
        "El primer satélite de comunicaciones de fabricación turca (2024). En órbita geoestacionaria, a 35.786 km, gira al mismo ritmo que la Tierra y permanece fijo en un punto del cielo.",
        "Первый спутник связи турецкого производства (2024). На геостационарной орбите высотой 35 786 км он вращается синхронно с Землёй и потому неподвижно висит в одной точке неба."),
    "Moon": ("Lune", "Luna", "Луна"),
    "Earth's only natural satellite and the main cause of the tides. It always shows the same face to Earth. Twelve people walked on its surface between 1969 and 1972.": (
        "Unique satellite naturel de la Terre et principale cause des marées. Elle présente toujours la même face à la Terre. Douze personnes ont marché à sa surface entre 1969 et 1972.",
        "El único satélite natural de la Tierra y la principal causa de las mareas. Siempre muestra la misma cara a la Tierra. Doce personas caminaron por su superficie entre 1969 y 1972.",
        "Единственный естественный спутник Земли и главная причина приливов. Она всегда обращена к Земле одной стороной. С 1969 по 1972 год по её поверхности прошли двенадцать человек."),
    "Mars": ("Mars", "Marte", "Марс"),
    "24 h 37 min": ("24 h 37 min", "24 h 37 min", "24 ч 37 мин"),
    "Its red colour comes from iron oxide on the surface. It hosts Olympus Mons, the tallest volcano in the Solar System (about 22 km), and the 4,000 km long Valles Marineris canyon. Dust storms in its thin atmosphere sometimes engulf the whole planet. Its poles hold water and carbon dioxide ice.": (
        "Sa couleur rouge provient de l'oxyde de fer présent en surface. On y trouve Olympus Mons, le plus haut volcan du Système solaire (environ 22 km), et le canyon Valles Marineris, long de 4 000 km. Dans sa fine atmosphère, des tempêtes de poussière engloutissent parfois toute la planète. Ses pôles renferment de la glace d'eau et de dioxyde de carbone.",
        "Su color rojo procede del óxido de hierro de la superficie. Alberga el Olympus Mons, el volcán más alto del Sistema Solar (unos 22 km), y el cañón Valles Marineris, de 4.000 km de longitud. En su tenue atmósfera, las tormentas de polvo llegan a cubrir el planeta entero. Sus polos contienen hielo de agua y de dióxido de carbono.",
        "Красный цвет ему придаёт оксид железа на поверхности. Здесь находятся гора Олимп — самый высокий вулкан Солнечной системы (около 22 км) — и каньон долины Маринер длиной 4 000 км. Пылевые бури в его разреженной атмосфере порой охватывают всю планету. На полюсах лежат водяной и углекислотный лёд."),
    "Orbits very close to Mars and sinks about 2 metres each century; in tens of millions of years it is expected to break up into a ring.": (
        "Il orbite tout près de Mars et se rapproche d'environ 2 mètres par siècle ; d'ici quelques dizaines de millions d'années, il devrait se désagréger en anneau.",
        "Orbita muy cerca de Marte y desciende unos 2 metros por siglo; dentro de decenas de millones de años se espera que se desintegre y forme un anillo.",
        "Обращается очень близко к Марсу и снижается примерно на 2 метра за столетие; через десятки миллионов лет он, как ожидается, разрушится и превратится в кольцо."),
    "The smaller, more distant moon of Mars. A thick layer of dust makes its surface look smooth.": (
        "La plus petite et la plus éloignée des lunes de Mars. Une épaisse couche de poussière donne à sa surface un aspect lisse.",
        "La luna más pequeña y lejana de Marte. Una gruesa capa de polvo hace que su superficie parezca lisa.",
        "Меньший и более далёкий спутник Марса. Толстый слой пыли делает его поверхность гладкой на вид."),
    "Jupiter": ("Jupiter", "Júpiter", "Юпитер"),
    "9 h 56 min": ("9 h 56 min", "9 h 56 min", "9 ч 56 мин"),
    "The largest planet in the Solar System, with more than twice the mass of all the other planets combined. It is made of hydrogen and helium and has no solid surface. The Great Red Spot is a storm larger than Earth that has raged for at least 190 years. Its strong gravity traps many asteroids along its orbit (the Trojans).": (
        "La plus grande planète du Système solaire, plus de deux fois plus massive que toutes les autres réunies. Composée d'hydrogène et d'hélium, elle n'a pas de surface solide. La Grande Tache rouge est une tempête plus vaste que la Terre qui fait rage depuis au moins 190 ans. Sa forte gravité retient de nombreux astéroïdes le long de son orbite (les Troyens).",
        "El mayor planeta del Sistema Solar, con más del doble de la masa de todos los demás juntos. Está formado por hidrógeno y helio y carece de superficie sólida. La Gran Mancha Roja es una tormenta mayor que la Tierra que lleva activa al menos 190 años. Su fuerte gravedad atrapa numerosos asteroides a lo largo de su órbita (los troyanos).",
        "Крупнейшая планета Солнечной системы: её масса более чем вдвое превышает массу всех остальных планет вместе взятых. Она состоит из водорода и гелия и не имеет твёрдой поверхности. Большое красное пятно — шторм крупнее Земли, бушующий уже не менее 190 лет. Мощная гравитация удерживает вдоль её орбиты множество астероидов (троянцев)."),
    "The most volcanically active body in the Solar System, with more than 400 active volcanoes. Jupiter's tidal forces constantly heat its interior.": (
        "Le corps le plus volcanique du Système solaire, avec plus de 400 volcans actifs. Les forces de marée de Jupiter chauffent sans cesse son intérieur.",
        "El cuerpo con mayor actividad volcánica del Sistema Solar, con más de 400 volcanes activos. Las fuerzas de marea de Júpiter calientan sin cesar su interior.",
        "Самое вулканически активное тело Солнечной системы — более 400 действующих вулканов. Приливные силы Юпитера непрерывно разогревают его недра."),
    "Beneath its cracked ice shell there is thought to be more water than in all of Earth's oceans. NASA's Europa Clipper spacecraft is on its way to study it.": (
        "Sous sa croûte de glace fissurée se cacherait davantage d'eau que dans tous les océans terrestres. La sonde Europa Clipper de la NASA est en route pour l'étudier.",
        "Se cree que bajo su agrietada corteza de hielo hay más agua que en todos los océanos de la Tierra. La sonda Europa Clipper de la NASA está en camino para estudiarla.",
        "Считается, что под её растрескавшимся ледяным панцирем больше воды, чем во всех океанах Земли. Аппарат NASA Europa Clipper уже летит к ней для изучения."),
    "The largest moon in the Solar System, bigger than Mercury, and the only moon with its own magnetic field.": (
        "La plus grande lune du Système solaire, plus grande que Mercure, et la seule à posséder son propre champ magnétique.",
        "La mayor luna del Sistema Solar, más grande que Mercurio, y la única con campo magnético propio.",
        "Крупнейший спутник Солнечной системы, больше Меркурия, и единственный спутник с собственным магнитным полем."),
    "It has one of the most heavily cratered surfaces in the Solar System, almost unchanged for about 4 billion years.": (
        "Sa surface est l'une des plus cratérisées du Système solaire et n'a presque pas changé depuis environ 4 milliards d'années.",
        "Tiene una de las superficies con más cráteres del Sistema Solar, casi sin cambios desde hace unos 4.000 millones de años.",
        "Его поверхность — одна из самых изрытых кратерами в Солнечной системе и почти не менялась около 4 млрд лет."),
    "Saturn": ("Saturne", "Saturno", "Сатурн"),
    "10 h 33 min": ("10 h 33 min", "10 h 33 min", "10 ч 33 мин"),
    "The gas giant famous for its rings. The rings consist of billions of pieces of ice and rock, from dust grains to house-sized blocks, each on its own orbit around the planet. They span about 280,000 km yet are mostly only tens of metres thick. Saturn's average density is lower than that of water. After 128 new moons in 2025 and dozens more in 2026, it has 293 confirmed moons as of August 2026.": (
        "La géante gazeuse célèbre pour ses anneaux. Ceux-ci se composent de milliards de fragments de glace et de roche, du grain de poussière au bloc gros comme une maison, chacun sur sa propre orbite autour de la planète. Ils s'étendent sur environ 280 000 km mais ne mesurent le plus souvent que quelques dizaines de mètres d'épaisseur. La densité moyenne de Saturne est inférieure à celle de l'eau. Après 128 nouvelles lunes en 2025 et plusieurs dizaines en 2026, elle compte 293 lunes confirmées en août 2026.",
        "El gigante gaseoso famoso por sus anillos. Estos se componen de miles de millones de fragmentos de hielo y roca, desde granos de polvo hasta bloques del tamaño de una casa, cada uno en su propia órbita alrededor del planeta. Abarcan unos 280.000 km, pero en su mayor parte solo tienen decenas de metros de grosor. La densidad media de Saturno es inferior a la del agua. Tras 128 nuevas lunas en 2025 y decenas más en 2026, cuenta con 293 lunas confirmadas a agosto de 2026.",
        "Газовый гигант, знаменитый своими кольцами. Они состоят из миллиардов обломков льда и камня — от пылинок до глыб размером с дом, — и каждый движется вокруг планеты по своей орбите. Кольца простираются примерно на 280 000 км, но в большинстве мест толщиной всего в десятки метров. Средняя плотность Сатурна ниже плотности воды. После 128 новых спутников в 2025 году и ещё нескольких десятков в 2026-м на август 2026 года у него 293 подтверждённых спутника."),
    "Orbits inside the Encke Gap within the rings and keeps this 325 km wide gap open with its gravity, which makes it a 'shepherd moon'. A ridge of ring material piled up along its equator gives it a ravioli or walnut look.": (
        "Il orbite dans la division d'Encke, au sein des anneaux, et maintient ouverte par sa gravité cette brèche large de 325 km : c'est un « satellite berger ». Un bourrelet de matière annulaire accumulée le long de son équateur lui donne l'allure d'un ravioli ou d'une noix.",
        "Orbita dentro de la división de Encke, en los anillos, y mantiene abierto con su gravedad ese hueco de 325 km de ancho, por lo que es una «luna pastora». Una cresta de material de los anillos acumulado en su ecuador le da aspecto de ravioli o de nuez.",
        "Обращается в щели Энке внутри колец и своей гравитацией удерживает открытым этот промежуток шириной 325 км — это «спутник-пастух». Гребень из вещества колец, скопившегося вдоль экватора, придаёт ему вид равиоли или грецкого ореха."),
    "Only 8 km across, it orbits in the Keeler Gap near the outer edge of the A ring. As it passes, it raises waves along the edges of the gap that reach about 1.5 km in height.": (
        "Large de seulement 8 km, il circule dans la division de Keeler, près du bord externe de l'anneau A. À son passage, il soulève sur les bords de la brèche des vagues d'environ 1,5 km de haut.",
        "Con solo 8 km de diámetro, orbita en la división de Keeler, cerca del borde exterior del anillo A. A su paso levanta en los bordes del hueco ondas de unos 1,5 km de altura.",
        "Имея в поперечнике всего 8 км, он обращается в щели Килера у внешнего края кольца A. Проходя мимо, он поднимает по краям щели волны высотой около 1,5 км."),
    "Orbits just outside the A ring. A broad skirt of dust and ice around its equator gives it a flying-saucer shape.": (
        "Il orbite juste au-delà de l'anneau A. Une large collerette de poussière et de glace autour de son équateur lui donne la forme d'une soucoupe volante.",
        "Orbita justo fuera del anillo A. Un amplio faldón de polvo y hielo alrededor de su ecuador le da forma de platillo volante.",
        "Обращается сразу за кольцом A. Широкий «пояс» из пыли и льда вдоль экватора придаёт ему форму летающей тарелки."),
    "The inner shepherd of the narrow F ring. On each orbit it approaches the ring, pulls material out of it and leaves channels and knots behind.": (
        "Le berger intérieur de l'étroit anneau F. À chaque orbite, il s'approche de l'anneau, lui arrache de la matière et y laisse des sillons et des nœuds.",
        "El pastor interior del estrecho anillo F. En cada órbita se acerca al anillo, le arranca material y deja canales y nudos a su paso.",
        "Внутренний пастух узкого кольца F. На каждом витке он сближается с кольцом, вырывает из него вещество и оставляет каналы и сгустки."),
    "Orbits just outside the F ring. It was long thought to shepherd the ring together with Prometheus; a fine blanket of dust softens the look of its craters.": (
        "Il orbite juste à l'extérieur de l'anneau F. On a longtemps cru qu'il gardait l'anneau avec Prométhée ; un fin manteau de poussière adoucit l'aspect de ses cratères.",
        "Orbita justo fuera del anillo F. Durante mucho tiempo se pensó que pastoreaba el anillo junto con Prometeo; un fino manto de polvo suaviza el aspecto de sus cráteres.",
        "Обращается сразу за кольцом F. Долго считалось, что он «пасёт» кольцо вместе с Прометеем; тонкий слой пыли смягчает очертания его кратеров."),
    "Shares almost the same orbit as Janus. About every four years the two approach each other, swap orbits through their mutual gravity and move apart without colliding.": (
        "Il partage presque la même orbite que Janus. Tous les quatre ans environ, les deux lunes se rapprochent, échangent leurs orbites sous l'effet de leur attraction mutuelle et s'éloignent sans se percuter.",
        "Comparte casi la misma órbita que Jano. Aproximadamente cada cuatro años ambas lunas se acercan, intercambian sus órbitas por su atracción mutua y se separan sin chocar.",
        "Движется почти по той же орбите, что и Янус. Примерно раз в четыре года они сближаются, под действием взаимного притяжения меняются орбитами и расходятся, не сталкиваясь."),
    "The co-orbital partner of Epimetheus and the larger of the pair. It is heavily cratered; the two are thought to be remnants of a single body that broke apart.": (
        "Le partenaire co-orbital d'Épiméthée et le plus grand des deux. Fortement cratérisé, il formerait avec lui les restes d'un même corps brisé.",
        "La compañera coorbital de Epimeteo y la mayor de las dos. Está cubierta de cráteres; se cree que ambas son restos de un único cuerpo que se fragmentó.",
        "Соорбитальный партнёр Эпиметея и более крупный из пары. Он густо покрыт кратерами; считается, что оба — обломки одного распавшегося тела."),
    "Its giant 130 km Herschel crater earns it comparisons with the 'Death Star'. Its gravity clears the Cassini Division in the rings. Wobbles in its orbital motion suggest a young ocean may lie beneath its icy shell.": (
        "Son gigantesque cratère Herschel, large de 130 km, lui vaut d'être comparé à « l'Étoile de la mort ». Sa gravité dégage la division de Cassini dans les anneaux. Les oscillations de son mouvement orbital laissent penser qu'un jeune océan pourrait se cacher sous sa croûte glacée.",
        "Su gigantesco cráter Herschel, de 130 km, hace que se le compare con la «Estrella de la Muerte». Su gravedad despeja la división de Cassini en los anillos. Las oscilaciones de su movimiento orbital sugieren que bajo su corteza helada podría haber un océano joven.",
        "Гигантский кратер Гершель диаметром 130 км вызывает сравнения со «Звездой смерти». Его гравитация расчищает щель Кассини в кольцах. Колебания его орбитального движения указывают, что под ледяной корой может скрываться молодой океан."),
    "One of the brightest bodies in the Solar System, reflecting almost all the light that reaches it. Water vapour and ice grains erupt into space from the 'tiger stripes' at its south pole; these geysers feed the E ring. The salty ocean beneath its ice shell is a prime target in the search for life.": (
        "L'un des corps les plus brillants du Système solaire : il réfléchit presque toute la lumière qu'il reçoit. De la vapeur d'eau et des grains de glace jaillissent dans l'espace depuis les « rayures de tigre » de son pôle Sud ; ces geysers alimentent l'anneau E. L'océan salé sous sa croûte de glace est une cible de choix dans la recherche de la vie.",
        "Uno de los cuerpos más brillantes del Sistema Solar: refleja casi toda la luz que recibe. Desde las «rayas de tigre» de su polo sur brotan al espacio vapor de agua y granos de hielo; estos géiseres alimentan el anillo E. El océano salado bajo su corteza de hielo es un objetivo prioritario en la búsqueda de vida.",
        "Одно из самых светлых тел Солнечной системы: оно отражает почти весь падающий свет. Из «тигровых полос» у южного полюса в космос бьют водяной пар и ледяные частицы; эти гейзеры питают кольцо E. Солёный океан под ледяной корой — одна из главных целей в поисках жизни."),
    "Made almost entirely of water ice. The 445 km Odysseus crater and Ithaca Chasma, a 2,000 km canyon running three quarters of the way around the moon, are its most striking features. It shares its orbit with Telesto and Calypso.": (
        "Presque entièrement constitué de glace d'eau. Le cratère Odysseus, large de 445 km, et Ithaca Chasma, un canyon de 2 000 km qui fait les trois quarts du tour de la lune, en sont les traits les plus marquants. Il partage son orbite avec Télesto et Calypso.",
        "Formada casi por completo por hielo de agua. El cráter Odiseo, de 445 km, e Ithaca Chasma, un cañón de 2.000 km que recorre tres cuartas partes de la luna, son sus rasgos más llamativos. Comparte órbita con Telesto y Calipso.",
        "Почти целиком состоит из водяного льда. Самые заметные детали — кратер Одиссей диаметром 445 км и каньон Итака длиной 2 000 км, опоясывающий три четверти спутника. Делит свою орбиту с Телесто и Калипсо."),
    "Travels along Tethys's orbit 60° ahead of it, at the L4 Lagrange point, which makes it a 'Trojan moon'. A coating of fine icy dust leaves its surface surprisingly smooth.": (
        "Il précède Téthys de 60° sur son orbite, au point de Lagrange L4, ce qui en fait une « lune troyenne ». Un dépôt de fine poussière glacée rend sa surface étonnamment lisse.",
        "Avanza por la órbita de Tetis 60° por delante de ella, en el punto de Lagrange L4, lo que la convierte en una «luna troyana». Una capa de fino polvo helado deja su superficie sorprendentemente lisa.",
        "Движется по орбите Тефии на 60° впереди неё, в точке Лагранжа L4, поэтому считается «троянским спутником». Слой мелкой ледяной пыли делает его поверхность удивительно гладкой."),
    "Travels along Tethys's orbit 60° behind it, at the L5 point. Like Telesto it has a smooth, very bright surface, thought to be coated by ice grains raining down from the E ring.": (
        "Il suit Téthys à 60° sur son orbite, au point L5. Comme Télesto, il a une surface lisse et très brillante, sans doute recouverte de grains de glace tombés de l'anneau E.",
        "Sigue a Tetis en su órbita a 60° por detrás, en el punto L5. Como Telesto, tiene una superficie lisa y muy brillante, probablemente cubierta por granos de hielo que caen del anillo E.",
        "Следует за Тефией по её орбите в 60° позади, в точке L5. Как и Телесто, имеет гладкую, очень яркую поверхность — вероятно, её покрывают ледяные частицы, оседающие из кольца E."),
    "A dense mixture of ice and rock. The bright wisps on its trailing hemisphere are ice cliffs hundreds of metres high. A thin atmosphere of oxygen ions has been detected, and an ocean may lie beneath its surface.": (
        "Un mélange dense de glace et de roche. Les traînées claires de son hémisphère arrière sont des falaises de glace hautes de plusieurs centaines de mètres. On y a détecté une fine atmosphère d'ions oxygène, et un océan pourrait se trouver sous sa surface.",
        "Una densa mezcla de hielo y roca. Las vetas brillantes de su hemisferio posterior son acantilados de hielo de cientos de metros de altura. Se ha detectado una tenue atmósfera de iones de oxígeno y bajo su superficie podría haber un océano.",
        "Плотная смесь льда и камня. Светлые «прожилки» на ведомом полушарии — ледяные обрывы высотой в сотни метров. Обнаружена тонкая атмосфера из ионов кислорода, а под поверхностью может находиться океан."),
    "Travels along Dione's orbit 60° ahead of it. Its surface shows gullies carved by flows of dust.": (
        "Il précède Dioné de 60° sur son orbite. Sa surface montre des ravines creusées par des écoulements de poussière.",
        "Avanza por la órbita de Dione 60° por delante de ella. Su superficie muestra surcos excavados por flujos de polvo.",
        "Движется по орбите Дионы на 60° впереди неё. На поверхности видны борозды, прорезанные потоками пыли."),
    "Saturn's second-largest moon. A heavily cratered icy world around which an extremely thin atmosphere of oxygen and carbon dioxide has been detected.": (
        "La deuxième plus grande lune de Saturne. Un monde glacé criblé de cratères autour duquel on a détecté une atmosphère extrêmement ténue d'oxygène et de dioxyde de carbone.",
        "La segunda luna más grande de Saturno. Un mundo helado lleno de cráteres en torno al cual se ha detectado una atmósfera extremadamente tenue de oxígeno y dióxido de carbono.",
        "Второй по величине спутник Сатурна. Ледяной мир, густо покрытый кратерами; вокруг него обнаружена чрезвычайно разреженная атмосфера из кислорода и углекислого газа."),
    "The second-largest moon in the Solar System, bigger than Mercury. It is the only moon with a thick atmosphere: surface pressure is 1.5 times Earth's and the air is mostly nitrogen. Lakes, seas and rivers of liquid methane and ethane lie on its surface. The Huygens probe landed there in 2005, and NASA's Dragonfly rotorcraft is to be sent there as well.": (
        "La deuxième plus grande lune du Système solaire, plus grande que Mercure. C'est la seule lune dotée d'une atmosphère épaisse : la pression au sol vaut 1,5 fois celle de la Terre et l'air est surtout composé d'azote. Des lacs, des mers et des rivières de méthane et d'éthane liquides recouvrent sa surface. La sonde Huygens s'y est posée en 2005, et le drone à rotors Dragonfly de la NASA doit aussi y être envoyé.",
        "La segunda luna más grande del Sistema Solar, mayor que Mercurio. Es la única luna con una atmósfera densa: la presión en superficie es 1,5 veces la terrestre y el aire es sobre todo nitrógeno. En su superficie hay lagos, mares y ríos de metano y etano líquidos. La sonda Huygens aterrizó allí en 2005, y también se enviará el helicóptero Dragonfly de la NASA.",
        "Второй по величине спутник Солнечной системы, больше Меркурия. Единственный спутник с плотной атмосферой: давление у поверхности в 1,5 раза выше земного, воздух состоит в основном из азота. На поверхности — озёра, моря и реки из жидкого метана и этана. В 2005 году там сел зонд «Гюйгенс», а в будущем туда отправится винтокрылый аппарат NASA Dragonfly."),
    "An irregular body that looks like a sponge, covered in deep, sharp-rimmed craters. It is so porous that its density is about half that of water. Its rotation is chaotic: its axis tumbles unpredictably.": (
        "Un corps irrégulier qui ressemble à une éponge, couvert de cratères profonds aux bords nets. Il est si poreux que sa densité vaut environ la moitié de celle de l'eau. Sa rotation est chaotique : son axe bascule de façon imprévisible.",
        "Un cuerpo irregular con aspecto de esponja, cubierto de cráteres profundos de bordes afilados. Es tan poroso que su densidad es aproximadamente la mitad que la del agua. Su rotación es caótica: su eje se tambalea de forma impredecible.",
        "Неправильное тело, похожее на губку и покрытое глубокими кратерами с острыми краями. Оно настолько пористое, что его плотность примерно вдвое ниже плотности воды. Вращение хаотично: ось непредсказуемо кувыркается."),
    "The two-faced moon: its leading hemisphere is coal-dark while its trailing hemisphere is snow-bright. A ridge running along the equator, in places more than 13 km high, gives it a walnut shape.": (
        "La lune à deux visages : son hémisphère avant est noir comme le charbon, tandis que son hémisphère arrière est blanc comme la neige. Une crête qui longe l'équateur, haute par endroits de plus de 13 km, lui donne la forme d'une noix.",
        "La luna de dos caras: su hemisferio delantero es oscuro como el carbón, mientras que el trasero es blanco como la nieve. Una cresta que recorre el ecuador, de más de 13 km de altura en algunos puntos, le da forma de nuez.",
        "Двуликий спутник: ведущее полушарие у него чёрное как уголь, а ведомое — белое как снег. Хребет вдоль экватора, местами высотой более 13 км, придаёт ему форму грецкого ореха."),
    "Orbits Saturn backwards on a steeply tilted path, so it is thought to have formed elsewhere and been captured later by Saturn's gravity. Dark dust knocked off its surface forms the vast, faint Phoebe ring and darkens the leading face of Iapetus.": (
        "Elle tourne autour de Saturne à rebours, sur une orbite très inclinée : elle se serait donc formée ailleurs avant d'être capturée par la gravité de Saturne. La poussière sombre arrachée à sa surface forme l'immense et pâle anneau de Phœbé et assombrit la face avant de Japet.",
        "Gira alrededor de Saturno en sentido contrario y en una órbita muy inclinada, por lo que se cree que se formó en otro lugar y fue capturada más tarde por la gravedad de Saturno. El polvo oscuro desprendido de su superficie forma el enorme y tenue anillo de Febe y oscurece la cara delantera de Jápeto.",
        "Обращается вокруг Сатурна в обратном направлении по сильно наклонённой орбите, поэтому считается, что она сформировалась в другом месте и позже была захвачена гравитацией Сатурна. Тёмная пыль, выбитая с её поверхности, образует огромное тусклое кольцо Фебы и затемняет ведущую сторону Япета."),
    "Uranus": ("Uranus", "Urano", "Уран"),
    "Gas planet (ice giant)": ("Planète gazeuse (géante de glace)", "Planeta gaseoso (gigante helado)", "Газовая планета (ледяной гигант)"),
    "17 h 14 min (retrograde)": ("17 h 14 min (rétrograde)", "17 h 14 min (retrógrado)", "17 ч 14 мин (обратное)"),
    "Its axis is tilted about 98°, so it orbits practically on its side; each pole gets 42 years of daylight followed by 42 years of night. Methane in its atmosphere gives it a pale blue-green colour. It is grouped with the gas planets and, being rich in water, ammonia and methane ices, is also called an 'ice giant'. It has 13 thin, dark rings.": (
        "Son axe est incliné d'environ 98° : elle orbite donc pratiquement couchée sur le côté, et chaque pôle connaît 42 ans de jour suivis de 42 ans de nuit. Le méthane de son atmosphère lui donne une teinte bleu-vert pâle. Classée parmi les planètes gazeuses, elle est aussi appelée « géante de glace » car elle est riche en glaces d'eau, d'ammoniac et de méthane. Elle possède 13 anneaux fins et sombres.",
        "Su eje está inclinado unos 98°, de modo que orbita prácticamente tumbado; cada polo vive 42 años de día seguidos de 42 años de noche. El metano de su atmósfera le da un color verde azulado pálido. Se agrupa con los planetas gaseosos y, por ser rico en hielos de agua, amoníaco y metano, también se le llama «gigante helado». Tiene 13 anillos finos y oscuros.",
        "Его ось наклонена примерно на 98°, поэтому он движется по орбите практически «лёжа на боку»: на каждом полюсе 42 года длится день, а затем 42 года — ночь. Метан в атмосфере придаёт ему бледный голубовато-зелёный цвет. Его относят к газовым планетам, а из-за обилия водяного, аммиачного и метанового льда называют также «ледяным гигантом». У него 13 тонких тёмных колец."),
    "Its surface looks like a patchwork; the 20 km high Verona Rupes is the tallest known cliff in the Solar System.": (
        "Sa surface ressemble à un patchwork ; Verona Rupes, haute de 20 km, est la plus haute falaise connue du Système solaire.",
        "Su superficie parece un mosaico de retales; Verona Rupes, de 20 km de altura, es el acantilado más alto conocido del Sistema Solar.",
        "Её поверхность напоминает лоскутное одеяло; уступ Верона высотой 20 км — самый высокий известный обрыв в Солнечной системе."),
    "The brightest of Uranus's large moons, with the geologically youngest surface.": (
        "La plus brillante des grandes lunes d'Uranus, à la surface géologiquement la plus jeune.",
        "La más brillante de las grandes lunas de Urano, con la superficie geológicamente más joven.",
        "Самый яркий из крупных спутников Урана с геологически самой молодой поверхностью."),
    "The darkest of Uranus's large moons, with a very old, cratered surface.": (
        "La plus sombre des grandes lunes d'Uranus, à la surface très ancienne et criblée de cratères.",
        "La más oscura de las grandes lunas de Urano, con una superficie muy antigua y llena de cráteres.",
        "Самый тёмный из крупных спутников Урана с очень древней поверхностью, покрытой кратерами."),
    "The largest moon of Uranus; huge canyons and fault lines cross its surface.": (
        "La plus grande lune d'Uranus ; d'immenses canyons et failles sillonnent sa surface.",
        "La mayor luna de Urano; enormes cañones y fallas cruzan su superficie.",
        "Крупнейший спутник Урана; его поверхность пересекают огромные каньоны и разломы."),
    "The outermost large moon of Uranus; its old, cratered surface shows craters with dark floors.": (
        "La plus éloignée des grandes lunes d'Uranus ; sa surface ancienne est parsemée de cratères au fond sombre.",
        "La más exterior de las grandes lunas de Urano; su antigua superficie muestra cráteres de fondo oscuro.",
        "Самый далёкий из крупных спутников Урана; на его древней поверхности видны кратеры с тёмным дном."),
    "Neptune": ("Neptune", "Neptuno", "Нептун"),
    "16 h 6 min": ("16 h 6 min", "16 h 6 min", "16 ч 6 мин"),
    "The most distant planet from the Sun and invisible to the naked eye; it was discovered in 1846 after its position was predicted mathematically. With winds reaching 2,100 km/h it has the fiercest storms in the Solar System. Like Uranus it is counted among the gas planets and is also known as an 'ice giant'. Its largest moon, Triton, orbits backwards.": (
        "La planète la plus éloignée du Soleil, invisible à l'œil nu ; elle fut découverte en 1846 après que sa position eut été prédite par le calcul. Avec des vents atteignant 2 100 km/h, elle connaît les tempêtes les plus violentes du Système solaire. Comme Uranus, elle est rangée parmi les planètes gazeuses et qualifiée de « géante de glace ». Sa plus grande lune, Triton, tourne à rebours.",
        "El planeta más alejado del Sol e invisible a simple vista; se descubrió en 1846 después de que su posición se predijera matemáticamente. Con vientos de hasta 2.100 km/h, tiene las tormentas más violentas del Sistema Solar. Como Urano, se cuenta entre los planetas gaseosos y también se le llama «gigante helado». Su mayor luna, Tritón, gira en sentido contrario.",
        "Самая далёкая от Солнца планета, невидимая невооружённым глазом; её открыли в 1846 году после того, как её положение было предсказано математически. Ветры там достигают 2 100 км/ч — это самые свирепые бури в Солнечной системе. Как и Уран, её относят к газовым планетам и называют «ледяным гигантом». Крупнейший спутник, Тритон, обращается в обратную сторону."),
    "Neptune's second-largest moon, a dark, angular body just too small to pull itself into a sphere.": (
        "La deuxième plus grande lune de Neptune, un corps sombre et anguleux, juste trop petit pour avoir pris une forme sphérique.",
        "La segunda luna más grande de Neptuno, un cuerpo oscuro y anguloso, apenas demasiado pequeño para adoptar forma esférica.",
        "Второй по величине спутник Нептуна — тёмное угловатое тело, которому чуть-чуть не хватило массы, чтобы стать шаром."),
    "The only large moon that orbits against its planet's rotation; it is thought to have been captured from the Kuiper Belt. Nitrogen geysers erupt on its surface, where the temperature is −235 °C.": (
        "La seule grande lune qui tourne en sens inverse de la rotation de sa planète ; elle aurait été capturée dans la ceinture de Kuiper. Des geysers d'azote jaillissent à sa surface, où il fait −235 °C.",
        "La única luna grande que orbita en sentido contrario a la rotación de su planeta; se cree que fue capturada del cinturón de Kuiper. En su superficie, a −235 °C, brotan géiseres de nitrógeno.",
        "Единственный крупный спутник, обращающийся против вращения своей планеты; считается, что он был захвачен из пояса Койпера. На его поверхности, где −235 °C, извергаются азотные гейзеры."),
    "It has one of the most elongated orbits of any moon: its distance from Neptune varies between 1.4 and 9.6 million km.": (
        "Elle possède l'une des orbites les plus allongées de toutes les lunes : sa distance à Neptune varie entre 1,4 et 9,6 millions de km.",
        "Tiene una de las órbitas más alargadas de todas las lunas: su distancia a Neptuno varía entre 1,4 y 9,6 millones de km.",
        "У него одна из самых вытянутых орбит среди спутников: расстояние до Нептуна меняется от 1,4 до 9,6 млн км."),
}

# Uydu adları (yalın metin olarak tutulanlar): İngilizce -> (fr, es, ru)
NAMES = {
    "Pan": ("Pan", "Pan", "Пан"), "Daphnis": ("Daphnis", "Dafnis", "Дафнис"), "Atlas": ("Atlas", "Atlas", "Атлас"),
    "Prometheus": ("Prométhée", "Prometeo", "Прометей"), "Pandora": ("Pandore", "Pandora", "Пандора"),
    "Epimetheus": ("Épiméthée", "Epimeteo", "Эпиметей"), "Janus": ("Janus", "Jano", "Янус"),
    "Mimas": ("Mimas", "Mimas", "Мимас"), "Enceladus": ("Encelade", "Encélado", "Энцелад"),
    "Tethys": ("Téthys", "Tetis", "Тефия"), "Telesto": ("Télesto", "Telesto", "Телесто"),
    "Calypso": ("Calypso", "Calipso", "Калипсо"), "Dione": ("Dioné", "Dione", "Диона"),
    "Helene": ("Hélène", "Helena", "Елена"), "Rhea": ("Rhéa", "Rea", "Рея"), "Titan": ("Titan", "Titán", "Титан"),
    "Hyperion": ("Hypérion", "Hiperión", "Гиперион"), "Iapetus": ("Japet", "Jápeto", "Япет"),
    "Phoebe": ("Phœbé", "Febe", "Феба"), "Phobos": ("Phobos", "Fobos", "Фобос"), "Deimos": ("Déimos", "Deimos", "Деймос"),
    "Io": ("Io", "Ío", "Ио"), "Europa": ("Europe", "Europa", "Европа"), "Ganymede": ("Ganymède", "Ganímedes", "Ганимед"),
    "Callisto": ("Callisto", "Calisto", "Каллисто"), "Miranda": ("Miranda", "Miranda", "Миранда"),
    "Ariel": ("Ariel", "Ariel", "Ариэль"), "Umbriel": ("Umbriel", "Umbriel", "Умбриэль"),
    "Titania": ("Titania", "Titania", "Титания"), "Oberon": ("Obéron", "Oberón", "Оберон"),
    "Proteus": ("Protée", "Proteo", "Протей"), "Triton": ("Triton", "Tritón", "Тритон"),
    "Nereid": ("Néréide", "Nereida", "Нереида"),
}

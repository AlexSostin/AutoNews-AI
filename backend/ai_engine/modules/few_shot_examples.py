"""
Few-shot example articles for AI article generation.

These high-quality examples are injected into the generation prompt to teach the AI
the exact writing style, HTML structure, and tone we want.
3 examples covering: Electric SUV, PHEV Sedan, Electric Hatchback.
Updated: longer, more technical, with Driving Experience sections.
"""

# ─── Example 1: Electric SUV ────────────────────────────────────────────────────
EXAMPLE_SUV = """
<h2>2026 Zeekr 7X: A 421 hp Electric SUV That Starts Under $30,000</h2>

<p>Zeekr's latest SUV enters one of the most competitive segments in the EV market — and does so with numbers that demand attention. The 2026 Zeekr 7X pairs a dual-motor AWD system producing 421 hp with a 75.6 kWh battery good for 615 km (CLTC), all starting from CNY 209,900 (approximately $29,400). For context, that undercuts the Tesla Model Y by nearly $15,000 in China while offering more power and comparable range.</p>

<h2>Performance & Specs</h2>

<p>The powertrain tells the story Zeekr wants you to hear: this isn't a compliance EV, it's genuinely fast.</p>

<ul>
<li><strong>POWERTRAIN TYPE:</strong> BEV</li>
<li><strong>MOTOR 1 (front):</strong> Permanent Magnet Synchronous — 170 hp / 127 kW — drives front wheels</li>
<li><strong>MOTOR 2 (rear):</strong> Permanent Magnet Synchronous — 251 hp / 187 kW — drives rear wheels</li>
<li><strong>TOTAL SYSTEM OUTPUT:</strong> 421 hp (314 kW) — 543 N·m combined torque</li>
<li><strong>BATTERY:</strong> 75.6 kWh — LFP (Lithium Iron Phosphate) — CATL Qilin</li>
<li><strong>RANGE:</strong> 615 km (CLTC)</li>
<li><strong>0-100 km/h:</strong> 3.8 seconds</li>
<li><strong>TOP SPEED:</strong> 200 km/h</li>
<li><strong>DC FAST CHARGING:</strong> 200 kW peak — 10-80% in 24 minutes</li>
<li><strong>DIMENSIONS:</strong> 4,825 × 1,930 × 1,656 mm — Wheelbase: 2,925 mm</li>
<li><strong>CURB WEIGHT:</strong> 2,185 kg</li>
<li><strong>DRIVETRAIN:</strong> AWD (dual-motor)</li>
</ul>

<p>A 3.8-second sprint puts it in performance SUV territory — faster than a Porsche Macan Turbo EV — yet the LFP chemistry means the battery will tolerate years of frequent fast charging without significant degradation. The CATL Qilin cell-to-pack architecture eliminates traditional modules, packing more energy density into the same footprint while improving thermal management.</p>

<h2>Design & Interior</h2>

<p>The exterior borrows Zeekr's family design language: slim full-width LED light bars front and rear, flush door handles, and a roofline that tapers just enough to look athletic without sacrificing rear headroom. The 21-inch wheels fill the arches convincingly, and the 0.268 Cd drag coefficient is impressive for an SUV of this size.</p>

<p>Inside, a 16-inch AMOLED central display dominates the dashboard, angled slightly toward the driver and running on the Qualcomm 8295 chip — the same silicon found in the BMW iX and Mercedes EQS. The materials are a step above what you'd expect at this price — perforated Nappa leather on the seats, brushed aluminum trim panels, and a flat-bottom steering wheel with haptic buttons. Rear passengers get their own climate zone and a generous 1,005 mm of legroom. Cargo space measures 520 liters behind the second row, expanding to 1,260 liters with seats folded.</p>

<h2>Technology & Features</h2>

<p>Zeekr loads the 7X with hardware that usually lives in cars costing twice as much. The autonomous driving stack includes one LiDAR unit (Hesai AT128), five millimeter-wave radars, twelve ultrasonic sensors, and twelve cameras — enough for highway NOA (Navigate on Autopilot) at launch, with urban NOA planned via OTA. The 21-speaker Yamaha audio system is a genuine highlight, delivering spatial audio quality that rivals dedicated Harman Kardon setups in premium Germans. Additional features include a wireless phone charging pad, NFC key access, four USB-C ports, and a V2L (Vehicle-to-Load) output rated at 3.3 kW.</p>

<h2>Driving Experience</h2>

<p>Despite the 2,185 kg curb weight, the 7X handles with unexpected composure. The dual-motor AWD system distributes torque independently to each axle, providing genuine all-weather capability. The CDC (Continuously Damped Control) adaptive suspension constantly adjusts to road conditions — firm through sweeping motorway bends, compliant enough to absorb urban potholes without jarring occupants.</p>

<p>The steering is light at parking speeds and weights up progressively — it won't satisfy track-day enthusiasts, but for a family SUV the calibration is well-judged. NVH (noise, vibration, harshness) is another strong point: the double-laminated windshield and thick door seals keep highway wind noise to a murmur, and the electric motors are near-silent up to 80 km/h. Regenerative braking offers a true one-pedal driving mode that's smooth enough for highway cruising without unsettling passengers.</p>

<h2>Pricing & Availability</h2>

<ul>
<li>RWD Long Range (single motor, 615 km): CNY 209,900 (~$29,400)</li>
<li>AWD Performance (dual motor, 580 km): CNY 249,900 (~$35,000)</li>
<li>On sale in China; European launch expected H2 2026</li>
</ul>

<h2>Pros & Cons</h2>

<p><strong>Pros:</strong></p>
<ul>
<li>421 hp and 3.8s 0-100 — genuine performance SUV numbers at a mainstream price</li>
<li>LFP battery chemistry means better longevity and thermal stability than NMC competitors</li>
<li>LiDAR-equipped autonomous driving hardware is future-proof for OTA upgrades</li>
<li>Interior quality punches well above its price point — Nappa leather, AMOLED display, Yamaha audio</li>
</ul>

<p><strong>Cons:</strong></p>
<ul>
<li>615 km CLTC range will translate to roughly 460-480 km in real-world driving</li>
<li>2,185 kg curb weight is noticeable in tight corners despite the dual-motor setup</li>
<li>No Apple CarPlay or Android Auto — relies entirely on built-in apps</li>
<li>Limited global service network outside China could be an ownership concern</li>
</ul>

<h2>FreshMotors Verdict</h2>

<p>The Zeekr 7X isn't trying to be the cheapest or the fastest — it's targeting the uncomfortable middle ground where established brands charge premium prices for mediocre specs. At $29,400, it offers performance that rivals the $90,000 Porsche Macan EV, technology that matches the $50,000 BMW iX, and interior quality that embarrasses anything in its own price bracket. For buyers who care about what they get per dollar spent, the 7X makes the math very simple. This is the family SUV for someone who refuses to compromise on technology or performance — and doesn't see why they should pay European prices for it.</p>
""".strip()


# ─── Example 2: PHEV Sedan ──────────────────────────────────────────────────────
EXAMPLE_PHEV_SEDAN = """
<h2>2026 BYD Seal 06: A 200 km Electric Range PHEV Sedan for $14,000</h2>

<p>BYD's DM 5.0 platform makes its sedan debut with the 2026 Seal 06 — and the numbers are hard to argue with. A 200 km electric-only range (CLTC), 1,200 km total combined range, and a starting price of CNY 99,800 (approximately $14,000). This isn't a concept or a limited run; it's BYD's play for the volume sedan segment, priced to pull buyers away from petrol cars entirely.</p>

<h2>Performance & Specs</h2>

<ul>
<li><strong>POWERTRAIN TYPE:</strong> PHEV (DM 5.0)</li>
<li><strong>MOTOR (traction):</strong> Permanent Magnet Synchronous — 160 hp / 120 kW — 210 N·m — drives front wheels</li>
<li><strong>RANGE EXTENDER:</strong> 1.5L Naturally Aspirated — 74 kW (99 hp) — 126 N·m — acts primarily as a generator</li>
<li><strong>TOTAL SYSTEM OUTPUT:</strong> 160 hp (120 kW) combined</li>
<li><strong>BATTERY:</strong> 18.3 kWh — BYD Blade Battery (LFP)</li>
<li><strong>RANGE:</strong> 200 km electric-only (CLTC) + 1,200 km combined</li>
<li><strong>0-100 km/h:</strong> 7.9 seconds</li>
<li><strong>FUEL CONSUMPTION:</strong> 2.9 L/100km (hybrid mode, WLTC)</li>
<li><strong>DC FAST CHARGING:</strong> 18 kW peak — 30-80% in 35 minutes</li>
<li><strong>DIMENSIONS:</strong> 4,830 × 1,875 × 1,495 mm — Wheelbase: 2,790 mm</li>
<li><strong>CURB WEIGHT:</strong> 1,620 kg</li>
<li><strong>FUEL TANK:</strong> 48 L</li>
</ul>

<p>The DM 5.0 powertrain is an evolution of BYD's series-parallel PHEV architecture. The 1.5L engine rarely drives the wheels directly — instead, it spins the generator to keep the Blade Battery topped up, operating at its most efficient RPM range. When the battery has charge, the car runs as a pure EV. When it doesn't, the engine keeps the motor fed. BYD claims 2.9 L/100km fuel consumption in hybrid mode, which would make this one of the most fuel-efficient sedans on sale anywhere — for context, a Toyota Corolla Hybrid averages 4.3 L/100km.</p>

<h2>Design & Interior</h2>

<p>The Seal 06 adopts BYD's "Ocean Aesthetic" design language — a low, wide stance with a full-width LED light bar connecting slim headlights. The drag coefficient of 0.23 Cd is genuinely impressive for a car at this price, and it contributes directly to the range figures. The silhouette is distinctly fastback, more Audi A5 Sportback than traditional sedan.</p>

<p>The cabin is clean and driver-focused. A 12.8-inch rotating central screen (portrait for navigation, landscape for media) runs BYD's DiLink system, while a 10.25-inch digital instrument cluster handles essential driving information. Materials are a mix of soft-touch surfaces on the upper dashboard and textured plastics on the lower doors — not luxury, but well-executed for the price. The front seats offer 8-way electric adjustment with ventilation on the Long Range model. Trunk capacity is 450 liters — modest, but the flat load floor compensates.</p>

<h2>Technology & Features</h2>

<p>Standard equipment is generous: Level 2 ADAS with adaptive cruise control, lane keeping assist, and automatic emergency braking (5 radars, 8 cameras). The infotainment system supports 5G connectivity, voice control with natural language processing, and wireless Apple CarPlay/Android Auto — a rarity at this price. Notable extras include a 220V AC outlet in the trunk (3.3 kW) for powering external devices, a dashcam integrated into the rearview mirror, and a digital key via Bluetooth and NFC.</p>

<h2>Driving Experience</h2>

<p>In EV mode — which covers 200 km on a full charge — the Seal 06 is whisper-quiet and responsive. The 160 hp electric motor delivers instant torque off the line, making city driving effortless. The transition from pure EV to hybrid mode is nearly imperceptible; you'll notice it only by the soft hum of the 1.5L generator engaging at highway speeds.</p>

<p>The ride is tuned for comfort rather than sport. MacPherson struts up front and a multi-link rear suspension soak up rough surfaces competently, though there's noticeable body roll through tighter turns — inevitable at 1,620 kg. Steering is light and numb at center, which is perfectly fine for the daily commute this car is designed for. The regenerative braking is calibrated conservatively, blending smoothly with the hydraulic brakes — no jarring deceleration that unsettles passengers.</p>

<h2>Pricing & Availability</h2>

<ul>
<li>Standard Range (120 km EV): CNY 99,800 (~$14,000)</li>
<li>Long Range (200 km EV): CNY 119,800 (~$16,800)</li>
<li>Available now in China; Southeast Asian markets expected Q3 2026</li>
</ul>

<h2>Pros & Cons</h2>

<p><strong>Pros:</strong></p>
<ul>
<li>200 km electric-only range covers most daily commutes without burning fuel</li>
<li>CNY 99,800 starting price undercuts comparable petrol sedans — cheaper than a Corolla</li>
<li>2.9 L/100km claimed fuel consumption in hybrid mode is industry-leading</li>
<li>BYD Blade Battery is proven safe and durable across millions of units</li>
<li>Wireless Apple CarPlay/Android Auto included — rare at this price</li>
</ul>

<p><strong>Cons:</strong></p>
<ul>
<li>7.9s 0-100 — adequate but not exciting for enthusiasts</li>
<li>No AWD option available at launch — FWD only</li>
<li>18 kW DC fast charging is slow compared to pure EVs — not ideal for road trips on battery alone</li>
<li>450-liter trunk is smaller than segment leaders like the Hyundai Sonata</li>
</ul>

<h2>FreshMotors Verdict</h2>

<p>The Seal 06 represents the moment PHEVs stop being a compromise and start being the logical default. With 200 km of electric range, most owners will rarely visit a petrol station — your daily commute, school runs, and grocery trips happen entirely on electrons. At $14,000, it's cheaper than a base Honda Civic in most markets — but runs on electricity for daily driving. BYD is betting that for millions of buyers, this math ends the ICE vs. EV debate entirely. If you want a practical sedan that sips fuel, charges cheaply, and doesn't break the bank — the Seal 06 is hard to argue against.</p>
""".strip()


# ─── Example 3: Off-Road PHEV SUV ──────────────────────────────────────────────
EXAMPLE_OFFROAD_SUV = """
<h2>2026 BYD Leopard 5: 680 hp DMO Hybrid Goes From 0-100 in 4.8 Seconds</h2>

<p>The BYD Fang Cheng Bao Leopard 5 doesn't fit neatly into any existing category — and that's exactly the point. With 680 hp from its DMO (Dual Mode Off-road) hybrid platform, a 0-100 km/h time of 4.8 seconds, and genuine off-road hardware including three electronic differential locks and adjustable air suspension, the Leopard 5 blends supercar acceleration with Land Cruiser-grade capability. Starting at CNY 289,800 (approximately $40,600), it targets buyers who refuse to choose between performance and adventure.</p>

<h2>Performance & Specs</h2>

<p>At the heart of the Leopard 5 is BYD's DMO (Dual Mode Off-road) platform — a fundamentally different approach to hybrid power compared to the efficiency-focused DM-i system.</p>

<ul>
<li><strong>POWERTRAIN TYPE:</strong> PHEV (DMO platform)</li>
<li><strong>RANGE EXTENDER:</strong> 1.5T Turbocharged — 143 hp / 105 kW — primarily functions as a generator</li>
<li><strong>MOTOR 1 (front):</strong> Permanent Magnet Synchronous — 200 hp / 150 kW — drives front wheels</li>
<li><strong>MOTOR 2 (rear):</strong> Permanent Magnet Synchronous — 285 hp / 210 kW — drives rear wheels</li>
<li><strong>TOTAL SYSTEM OUTPUT:</strong> 680 hp (500 kW) — 760 N·m combined torque</li>
<li><strong>BATTERY:</strong> 31.8 kWh — BYD Blade Battery (LFP) — integrated into chassis for rigidity</li>
<li><strong>RANGE:</strong> 125 km electric-only (CLTC) + 1,200 km combined</li>
<li><strong>0-100 km/h:</strong> 4.8 seconds</li>
<li><strong>TOP SPEED:</strong> 180 km/h</li>
<li><strong>GROUND CLEARANCE:</strong> 200 mm (adjustable +70 mm / -70 mm via DiSus-P air suspension)</li>
<li><strong>APPROACH / DEPARTURE ANGLES:</strong> 33° / 30°</li>
<li><strong>WADING DEPTH:</strong> 1,000 mm</li>
<li><strong>DIMENSIONS:</strong> 4,890 × 1,970 × 1,920 mm — Wheelbase: 2,800 mm</li>
<li><strong>CURB WEIGHT:</strong> 2,900 kg</li>
<li><strong>DRIVETRAIN:</strong> AWD — permanent all-wheel drive with three electronic differential locks</li>
</ul>

<p>The 680 hp combined output is staggering for a vehicle designed to climb sand dunes. The twin electric motors deliver instantaneous torque to both axles — crucial for off-road traction — while the 1.5T turbo engine serves primarily as a range-extending generator. With the battery depleted, the Leopard 5 still has 1,075 km of fuel range. The three electronic differential locks (front, center, rear) can be locked individually or all at once, providing true 4x4 capability that rivals the Mercedes G-Class or Toyota Land Cruiser 300.</p>

<h2>Design & Interior</h2>

<p>The "Leopard Aesthetics" design language gives the Leopard 5 a boxy, commanding silhouette. The front end features a signature LED matrix grille flanked by split headlights, while flared wheel arches and side-mounted exhaust exits (for the generator) add visual aggression. The proportions are deliberately Land Rover Defender — wide, tall, and unapologetically squared-off.</p>

<p>Inside, the cabin blends rugged aesthetics with genuine luxury. A tri-screen setup includes a 15.6-inch central infotainment hub, a 12.3-inch digital dashboard, and a dedicated 12.3-inch passenger entertainment display. The center console features crystal-look physical toggle switches for off-road modes, and a retractable gear selector that emerges when the vehicle powers on. Nappa leather seats with diamond quilting, a panoramic sunroof, and ambient lighting across 64 colors — this interior wouldn't feel out of place in a vehicle costing twice as much.</p>

<h2>Technology & Features</h2>

<p>The technology stack is built around the DiSus-P intelligent hydraulic suspension — the same system found in the BYD Yangwang U8. It can adjust ride height by 140 mm in real-time, automatically raising the body when sensors detect rough terrain and lowering it for highway stability. The 6 kW V2L (Vehicle-to-Load) output is a standout: powerful enough to run a campsite, power tools, or charge another EV in an emergency.</p>

<p>Safety is handled by an L2+ ADAS suite with 360-degree transparent chassis viewing — critical for navigating boulder-strewn trails where even mirrors can't show you what's underneath. Additional features include a Sentry Mode with 360-degree recording, tank-turn capability on loose surfaces, and a built-in tire pressure monitoring system with automatic deflation for sand driving.</p>

<h2>Driving Experience</h2>

<p>On asphalt, the Leopard 5 disguises its 2,900 kg curb weight remarkably well. The DiSus-P suspension keeps body roll in check through highway sweepers, and the low center of gravity (courtesy of the chassis-integrated Blade Battery) prevents the top-heavy feeling common in traditional body-on-frame SUVs. The 4.8-second 0-100 sprint is genuinely shocking — hit the throttle hard and the instant torque from both electric motors pins you into the quilted leather seats.</p>

<p>Off-road is where the Leopard 5 truly differentiates itself. The combination of 760 N·m torque, three locking differentials, and 270 mm of ground clearance (raised mode) means it will crawl over obstacles that would stop most crossovers dead. The tank-turn mode — rotating the vehicle within its own footprint using counter-rotating motors — is more party trick than practical necessity, but demonstrates the precision of the electric drivetrain's torque vectoring. The 1,000 mm wading depth is also class-leading, exceeding the Land Cruiser's 700 mm.</p>

<h2>Pricing & Availability</h2>

<ul>
<li>Standard (31.8 kWh, 1,200 km combined): CNY 289,800 (~$40,600)</li>
<li>On sale in China now; Middle East markets expected late 2026</li>
<li>European launch timing not yet confirmed</li>
</ul>

<h2>Pros & Cons</h2>

<p><strong>Pros:</strong></p>
<ul>
<li>680 hp and 4.8s 0-100 deliver supercar acceleration in an off-road package</li>
<li>Three electronic differential locks and 1,000 mm wading depth rival the G-Class</li>
<li>DiSus-P air suspension with 140 mm travel adapts to any terrain automatically</li>
<li>6 kW V2L output powers campsites, tools, or even other EVs</li>
<li>Premium interior with Nappa leather, tri-screen setup, and crystal toggles</li>
</ul>

<p><strong>Cons:</strong></p>
<ul>
<li>2,900 kg curb weight impacts braking distances and tire wear significantly</li>
<li>125 km electric-only range is modest for the 31.8 kWh battery</li>
<li>Limited global service network — Fang Cheng Bao is still a new sub-brand</li>
<li>Complex DMO hybrid system may be expensive to maintain outside BYD's network</li>
</ul>

<h2>FreshMotors Verdict</h2>

<p>The Leopard 5 is the "Swiss Army knife" of the SUV world — but one where every tool is genuinely sharp. It bridges the gap between a refined daily commuter and a hardcore weekend off-roader, something the Toyota Land Cruiser and Mercedes G-Class have attempted for decades at two or three times the price. For buyers who want supercar acceleration, serious off-road capability, and a luxury interior without choosing between them, the Leopard 5 is currently in a league of its own. The only question is whether BYD can build the global service network fast enough to match its ambitions.</p>
""".strip()


# ─── Combined for prompt injection ──────────────────────────────────────────────
def get_few_shot_examples(provider='gemini') -> str:
    """Return formatted few-shot examples for the article generation prompt.
    
    Gemini (1M context): all 3 full examples.
    Groq (128K context but limited output): 1 compact example to save tokens for data.
    """
    if provider == 'groq':
        # Groq gets 1 example to save context for analysis data
        return f"""
═══════════════════════════════════════════════
REFERENCE EXAMPLE — Match this style, structure, depth, and HTML quality
═══════════════════════════════════════════════
Your output MUST match this level of:
- Proper HTML formatting (<h2>, <p>, <ul>, <li>, <strong>)
- DETAILED technical specs with real-world context
- Driving Experience section that brings the car to life
- Honest pros & cons, FreshMotors Verdict
- Target length: 800-1200 words

{EXAMPLE_OFFROAD_SUV}

═══════════════════════════════════════════════
END OF EXAMPLE — Now write YOUR article following the same patterns
═══════════════════════════════════════════════
"""
    
    # Gemini gets all 3 examples for maximum style guidance
    return f"""
═══════════════════════════════════════════════
REFERENCE EXAMPLES — Match this style, structure, depth, and HTML quality
═══════════════════════════════════════════════
Study these examples carefully. Your output MUST match this level of:
- Proper HTML formatting (<h2>, <p>, <ul>, <li>, <strong>)
- DETAILED technical specs with real-world context and implications
- Driving Experience sections that bring the car to life
- Honest pros & cons with specific, measurable claims
- Competitor comparisons backed by real data
- FreshMotors Verdict that tells the reader WHO this car is for
- Target length: 800-1200 words

--- EXAMPLE 1 (Electric SUV) ---
{EXAMPLE_SUV}

--- EXAMPLE 2 (PHEV Sedan) ---
{EXAMPLE_PHEV_SEDAN}

--- EXAMPLE 3 (Off-Road PHEV SUV) ---
{EXAMPLE_OFFROAD_SUV}

═══════════════════════════════════════════════
END OF EXAMPLES — Now write YOUR article following the same patterns
═══════════════════════════════════════════════
"""

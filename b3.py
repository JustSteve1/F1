import fastf1

YEAR = 2025

found = []

for test_number in range(1, 5):       # generous upper bound
    for session_number in range(1, 6):
        try:
            print(f"Trying test={test_number}, session={session_number} ...")

            session = fastf1.get_testing_session(
                YEAR,
                test_number=test_number,
                session_number=session_number
            )

            # IMPORTANT:
            # We only try to load *lightly* – this is the only way to know if it exists
            session.load(telemetry=False, weather=False)

            event = session.event

            found.append({
                "test_number": test_number,
                "session_number": session_number,
                "event_name": event["EventName"],
                "location": event["Location"],
                "country": event["Country"],
                "date": event["EventDate"]
            })

            print("  -> OK")

        except Exception as e:
            # Most combinations simply don't exist
            print("  -> not found")

print("\nFound testing sessions:")
for row in found:
    print(row)

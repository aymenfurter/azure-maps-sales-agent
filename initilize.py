import os
from dotenv import load_dotenv


def check_azure_maps_key():
    """Check if Azure Maps API key is set in environment variables."""
    azure_maps_key = os.environ.get("AZURE_MAPS_KEY")

    if not azure_maps_key:
        print("\n⚠️ WARNING: AZURE_MAPS_KEY environment variable not found!")
        print("This application requires an Azure Maps API key.")
        print("You can set it by running:")
        print("export AZURE_MAPS_KEY=your_key_here")
    else:
        print("✓ Azure Maps API key found in environment variables.")


def main():
    load_dotenv(override=True)

    print("Sales Day Planning Assistant - Initialization")
    print("---------------------------------------------")

    check_azure_maps_key()

    print("\nInitialization completed. You can now start the application using 'python main.py'")


if __name__ == "__main__":
    main()

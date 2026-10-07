"""
Application Entry Point for Online Exam Seating & Invigilation Planner.
Invokes create_app() and starts the development server.
"""

import os
import click
from app import create_app

# Retrieve environment setting, defaulting to development
env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)


@app.cli.command("seed")
@click.option("--reset", is_flag=True, default=False, help="Wipe existing records before seeding.")
def seed_command(reset):
    """Seed the database with realistic polytechnic examination data."""
    from seed import run_seeder
    run_seeder(reset=reset)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=app.config.get("DEBUG", True),
    )

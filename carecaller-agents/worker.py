"""Root-level entry point so you can run: uv run worker.py dev"""

if __name__ == "__main__":
    from carecaller_agents.worker import cli, worker_options

    cli.run_app(worker_options)

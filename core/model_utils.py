import random
import string


def generate_random_key():
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(10))


def run_agent_synchronously(agent, input_string, deps=None):
    """
    Run a PydanticAI agent synchronously.

    Args:
        agent: The PydanticAI agent to run
        input_string: The input string to pass to the agent
        deps: Optional dependencies to pass to the agent

    Returns:
        The result of the agent run

    Raises:
        RuntimeError: If the agent execution fails
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # Pass deps to the agent.run method if provided
        if deps is not None:
            result = loop.run_until_complete(agent.run(input_string, deps=deps))
        else:
            result = loop.run_until_complete(agent.run(input_string))
        return result
    except Exception as e:
        raise RuntimeError(f"Agent execution failed: {str(e)}") from e

import random
import string


def generate_random_key():
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(10))


def run_agent_synchronously(agent, input_string):
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(agent.run(input_string))
        return result
    except Exception as e:
        raise RuntimeError(f"Agent execution failed: {str(e)}") from e
    finally:
        if not loop.is_closed():
            loop.close()

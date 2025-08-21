from ag import graph


def print_stream(stream):
    for s in stream:
        try:
            message = s["messages"][-1]
        except Exception:
            print(s)
            continue
        if isinstance(message, tuple):
            print(message)
        elif hasattr(message, "pretty_print"):
            message.pretty_print()
        else:
            print(message)


config = {"configurable": {"thread_id": "1"}}


def conversation_loop() -> None:
    print("Type 'exit' or 'quit' to leave.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if user_input.lower() in ("exit", "quit", ":q"):
            print("Bye.")
            break
        if not user_input:
            continue
        inputs = {"messages": [("user", user_input)]}
        print_stream(graph.stream(inputs, config=config, stream_mode="values"))
        print()


if __name__ == "__main__":
    conversation_loop()
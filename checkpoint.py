import sqlite3
# from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langgraph.checkpoint.sqlite import SqliteSaver

# LangGraph encrypted checkpointing (requires LANGGRAPH_AES_KEY env var)
# serde = EncryptedSerializer.from_pycryptodome_aes()
# checkpointer = SqliteSaver(sqlite3.connect("checkpoint.db"), serde=serde)

conn = sqlite3.connect("checkpoint.db", check_same_thread=False)
checkpointer = SqliteSaver(conn) 
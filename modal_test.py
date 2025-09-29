import os

import modal

app = modal.App()


@app.function(secrets=[modal.Secret.from_name("custom-secret")])
def f():
    print(os.environ["SUPABASE_ANON_KEY"])


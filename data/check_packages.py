import importlib.metadata

packages = ["PyYAML", "requests", "python-dotenv"]

for pkg in packages:
    try:
        dist = importlib.metadata.distribution(pkg)
        print(f"✅ {pkg}")
        print(f" Version : {dist.version}")
        print(f" Location: {dist.locate_file('')}")
        print(f" Requires: {dist.requires}\n")
    except importlib.metadata.PackageNotFoundError:
        print(f"❌ {pkg} not installed\n")
import io
import os
import tarfile
import httpx
from languages import registry

def fetch_repository_archive(
    owner: str,
    repo: str,
    ref: str,
    github_token: str = None,
    target_extension: str = None
) -> dict:
    """
    Downloads the repository tarball from GitHub for a specific ref (commit SHA, branch, tag),
    decompresses it in-memory, and extracts all files matching target extension or registered language extensions.
    Returns a dict: file_path (str) -> code_bytes (bytes).
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/tarball/{ref}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Diff-Guard"
    }
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        
    buffer = io.BytesIO()
    
    # Stream the download sequentially into our memory buffer
    with httpx.stream("GET", url, headers=headers, follow_redirects=True) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes(chunk_size=16384):
            buffer.write(chunk)
            
    buffer.seek(0)
    
    files_data = {}
    
    # Decompress and stream read from the in-memory tarball
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                # GitHub tarball root dir is dynamic (e.g. owner-repo-sha/), strip it
                parts = member.name.split("/", 1)
                repo_relative_path = parts[1] if len(parts) > 1 else member.name
                
                should_extract = False
                if target_extension is not None:
                    should_extract = member.name.endswith(target_extension)
                else:
                    should_extract = (
                        registry.is_supported(repo_relative_path) or
                        os.path.basename(repo_relative_path) == "go.mod"
                    )
                
                if should_extract:
                    f = tar.extractfile(member)
                    if f:
                        files_data[repo_relative_path] = f.read()
                        
    return files_data

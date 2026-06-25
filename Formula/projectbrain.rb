class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/1e3f8262afc9bd11ac5bbcaf2775e25aa4ed6813.tar.gz"
  version "0.2.3"
  sha256 "78a99de58d8674d274e55fb7df6eb9546d52b558645d8b532e782660f47c08ca"
  license "MIT"
  head "https://github.com/yinshaojun001/projectbrain.git", branch: "main"

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
    system libexec/"bin/python", "-m", "pip", "install", "#{buildpath}[api]"
  end

  test do
    assert_match "usage: projectbrain", shell_output("#{bin}/projectbrain --help")
    assert_match "usage: codex-brain", shell_output("#{bin}/codex-brain --help")
    assert_match "usage: projectbrain brain", shell_output("#{bin}/projectbrain brain --help")

    doctor_output = shell_output("#{bin}/projectbrain doctor")
    assert_match "status", doctor_output
    assert_match "ok", doctor_output

    system libexec/"bin/python", "-c", "import fastapi, uvicorn, jinja2, projectbrain_api"

    (testpath/"repo").mkpath
    shell_output("#{bin}/codex-brain --project #{testpath}/repo --no-ui --no-extract --codex-command true")
    refute_path_exists testpath/"repo"/".projectbrain"/"brain"/"conversations.jsonl"
  end
end

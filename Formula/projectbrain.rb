class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/4134985f241af51954e4ccc09e327b6fe239464f.tar.gz"
  version "0.2.3"
  sha256 "ca385a989e809f37f1c05701f9592fd2a9ebd9e1d6ad70f1f24f9e5dfd7cc5c3"
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

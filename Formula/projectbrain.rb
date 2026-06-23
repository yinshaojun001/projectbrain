class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/77c48930a107f86194dc303c5e1b7d0bd0c052df.tar.gz"
  version "0.2.2"
  sha256 "25766f5166ad38e7f67f25fb6dc0b0319f7a0a2df5028540d63eea86f02494a1"
  license "MIT"
  head "https://github.com/yinshaojun001/projectbrain.git", branch: "main"

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage: projectbrain", shell_output("#{bin}/projectbrain --help")
    assert_match "usage: codex-brain", shell_output("#{bin}/codex-brain --help")
    assert_match "usage: projectbrain brain", shell_output("#{bin}/projectbrain brain --help")

    doctor_output = shell_output("#{bin}/projectbrain doctor")
    assert_match "status", doctor_output
    assert_match "ok", doctor_output

    (testpath/"repo").mkpath
    shell_output("#{bin}/codex-brain --project #{testpath}/repo --no-ui --no-extract --codex-command true")
    assert_path_exists testpath/"repo"/".projectbrain"/"brain"
  end
end

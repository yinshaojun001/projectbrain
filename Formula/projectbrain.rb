class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/3be0f56de1fa10bf5fe0a2479f6f95da14c3f96a.tar.gz"
  version "0.2.2"
  sha256 "d77344ae09b3c8bbca83ffa7ca84e769f87c4cdad8d09a2c8a521b8b45c4da5c"
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

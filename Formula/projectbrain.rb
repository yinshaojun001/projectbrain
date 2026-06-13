class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/103bd14a411c5e63a008f2d3c24e3696a1867313.tar.gz"
  version "0.2.0"
  sha256 "9ddcdb082315a514c885b5a975e59daf6cd43d1fe089bc6d13d83c1d874499a1"
  license "MIT"

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "status", shell_output("#{bin}/projectbrain doctor")
    assert_match "ok", shell_output("#{bin}/projectbrain doctor")
  end
end

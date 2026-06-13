class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/83712fda58d719176c899976f1c536f92d234351.tar.gz"
  version "0.2.2"
  sha256 "c3dea96d5d17f67a0fdc8e63914ae6b799de7b299fdca0d821d42cb5297929a7"
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

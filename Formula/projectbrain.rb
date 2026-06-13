class Projectbrain < Formula
  include Language::Python::Virtualenv

  desc "Local-first project cognition and impact analysis layer for AI coding agents"
  homepage "https://github.com/yinshaojun001/projectbrain"
  url "https://github.com/yinshaojun001/projectbrain/archive/de321ca616a67672a6fd6565f3af55c4240e599e.tar.gz"
  version "0.2.1"
  sha256 "d4124ae426221a0e67aaa7660b178c111adbd55c3e90952744c055ae88ccdb27"
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

class Kshield < Formula
  desc "Local-first AI code review firewall"
  homepage "https://github.com/YTT-Global/kshield"
  version "1.0.0"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/YTT-Global/kshield/releases/download/v#{version}/kshield-aarch64-apple-darwin.tar.gz"
      sha256 "REPLACE_AFTER_MACOS_ARM64_BUILD"
    else
      url "https://github.com/YTT-Global/kshield/releases/download/v#{version}/kshield-x86_64-apple-darwin.tar.gz"
      sha256 "REPLACE_AFTER_MACOS_X86_BUILD"
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/YTT-Global/kshield/releases/download/v#{version}/kshield-aarch64-unknown-linux-gnu.tar.gz"
      sha256 "849c32d1b1d873b1bb182f54550bbc40400db46f15505b0c4bb34fa6475733d3"
    else
      url "https://github.com/YTT-Global/kshield/releases/download/v#{version}/kshield-x86_64-unknown-linux-gnu.tar.gz"
      sha256 "7e4234745e19033709af9a175670dfd796e0e7cfbe6de0f6f9f8b3bdccabde85"
    end
  end

  def install
    bin.install "kshield"
  end

  def caveats
    <<~EOS
      Run this inside any git repo to get started:

        kshield init

      This installs a pre-commit hook and sets up the backend (SQLite, no Docker needed).

      To check status at any time:
        kshield status
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/kshield --version")
  end
end

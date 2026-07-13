class Kshield < Formula
  desc "Local-first AI code review firewall"
  homepage "https://github.com/YTTGlobalServices/kshield"
  version "1.0.0"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/YTTGlobalServices/kshield/releases/download/v#{version}/kshield-aarch64-apple-darwin.tar.gz"
      sha256 "018ecd73ac71641382571f05cc10788dcf4f0319c1f132905ae3b00edef8935a"
    else
      url "https://github.com/YTTGlobalServices/kshield/releases/download/v#{version}/kshield-x86_64-apple-darwin.tar.gz"
      sha256 "81fcbd439887f6e2acbb2b6d9287f2d50eb5571ec386246f87c2755bbf1393cb"
    end
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/YTTGlobalServices/kshield/releases/download/v#{version}/kshield-aarch64-unknown-linux-gnu.tar.gz"
      sha256 "REPLACE_AFTER_LINUX_ARM64_BUILD"
    else
      url "https://github.com/YTTGlobalServices/kshield/releases/download/v#{version}/kshield-x86_64-unknown-linux-gnu.tar.gz"
      sha256 "REPLACE_AFTER_LINUX_X86_BUILD"
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

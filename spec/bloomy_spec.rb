# frozen_string_literal: true

RSpec.describe "Bloomy Versioning" do
  context "when interacting with the gem" do
    it "has a version number" do
      expect(Bloomy::VERSION).not_to be nil
    end
  end
end

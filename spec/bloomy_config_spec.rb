# frozen_string_literal: true

RSpec.describe "Config Operations" do
  let(:username) { ENV.fetch("USERNAME", nil) }
  let(:password) { ENV.fetch("PASSWORD", nil) }
  let(:config_file) { File.expand_path("~/.bloomy/config.yaml") }
  let(:config) { Bloomy::Configuration.new }

  context "when configuring the API key" do
    before do
      FileUtils.rm_f(config_file)
      config.configure_api_key(username, password, store_key: true)
    end

    it "returns an API key" do
      expect(config.api_key).not_to be nil
    end

    it "stores the API key in ~/.bloomy/config.yaml" do
      expect(File.exist?(config_file)).to be true
    end

    it "loads the stored API key" do
      loaded_config = YAML.load_file(config_file)
      expect(loaded_config[:api_key]).not_to be nil
    end
  end
end

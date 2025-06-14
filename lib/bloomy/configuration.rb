# frozen_string_literal: true

require "fileutils"
require "faraday"
require "yaml"

module Bloomy
  # The Configuration class is responsible for managing the authentication
  class Configuration
    attr_accessor :api_key

    # Initializes a new Configuration instance
    #
    # @param [String, nil] api_key Pass an optional API key
    # @example
    #   config = Bloomy::Configuration.new(api_key)
    def initialize(api_key = nil)
      @api_key = api_key || ENV["BG_API_KEY"] || load_api_key
    end

    # Configures the API key using the provided username and password
    #
    # @param username [String] the username for authentication
    # @param password [String] the password for authentication
    # @param store_key [Boolean] whether to store the API key (default: false)
    # @return [void]
    # @note This method only fetches and stores the API key if it is currently nil.
    #   It saves the key under '~/.bloomy/config.yaml' if 'store_key: true' is passed.
    # @example
    #   config.configure_api_key("user", "pass", store_key: true)
    #   config.api_key
    #   # => 'xxxx...'
    def configure_api_key(username, password, store_key: false)
      @api_key = fetch_api_key(username, password)
      store_api_key if store_key
    end

    private

    # Fetches the API key using the provided username and password
    #
    # @param username [String] the username for authentication
    # @param password [String] the password for authentication
    # @return [String] the fetched API key
    def fetch_api_key(username, password)
      conn = Faraday.new(url: "https://app.bloomgrowth.com")
      response = conn.post("/Token") do |req|
        req.headers["Content-Type"] = "application/x-www-form-urlencoded"
        req.body = URI.encode_www_form(
          grant_type: "password",
          userName: username,
          password: password
        )
      end

      unless response.success?
        raise "Failed to fetch API key: #{response.status} - #{response.body}"
      end

      JSON.parse(response.body)["access_token"]
    end

    # Stores the API key in a local configuration file
    #
    # @return [void]
    # @raise [RuntimeError] if the API key is nil
    # @example
    #   config.store_api_key
    def store_api_key
      raise "API key is nil" if @api_key.nil?

      FileUtils.mkdir_p(config_dir)
      File.write(config_file, {version: 1, api_key: @api_key}.to_yaml)
    end

    # Loads the API key from a local configuration file
    #
    # @return [String, nil] the loaded API key or nil if the file does not exist
    def load_api_key
      return nil unless File.exist?(config_file)

      YAML.load_file(config_file)[:api_key]
    end

    # Returns the directory path for the configuration file
    #
    # @return [String] the directory path for the configuration file
    def config_dir
      File.expand_path("~/.bloomy")
    end

    # Returns the file path for the configuration file
    #
    # @return [String] the file path for the configuration file
    def config_file
      File.join(config_dir, "config.yaml")
    end
  end
end

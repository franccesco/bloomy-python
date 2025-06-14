# frozen_string_literal: true

require "bloomy/utils/get_user_id"

module Bloomy
  class Headline
    include Bloomy::Utilities::UserIdUtility
    # Initializes a new headline instance
    #
    # @param conn [Object] the connection object to interact with the API
    def initialize(conn)
      @conn = conn
    end

    # Creates a new headline
    #
    # @param meeting_id [Integer] the ID of the meeting
    # @param title [String] the title of the headline
    # @param owner_id [Integer] the ID of the headline owner
    # @param notes [String] additional notes for the headline
    # @return [Hash] containing id, title, owner_details, and notes_url
    def create(meeting_id:, title:, owner_id: user_id, notes: nil)
      response = @conn.post("/api/v1/L10/#{meeting_id}/headlines",
        {title: title, ownerId: owner_id, notes: notes}.to_json)
      raise "Failed to create headline" unless response.status == 200

      {
        id: response.body["Id"],
        title: response.body["Name"],
        owner_details: {id: response.body["OwnerId"]},
        notes_url: response.body["DetailsUrl"]
      }
    end

    # Updates a headline
    #
    # @param headline_id [Integer] the ID of the headline to update
    # @param title [String] the new title of the headline
    # @return [Boolean] true if update was successful
    def update(headline_id:, title:)
      response = @conn.put("/api/v1/headline/#{headline_id}", {title: title}.to_json)
      raise "Failed to update headline" unless response.status == 200
      true
    end

    # Get headline details
    #
    # @param headline_id [Integer] the ID of the headline
    # @return [Hash] containing id, title, notes_url, meeting_details,
    #                owner_details, archived, created_at, and closed_at
    def details(headline_id)
      response = @conn.get("/api/v1/headline/#{headline_id}?Include_Origin=true")
      raise "Failed to get headline details" unless response.status == 200

      {
        id: response.body["Id"],
        title: response.body["Name"],
        notes_url: response.body["DetailsUrl"],
        meeting_details: {
          id: response.body["OriginId"],
          title: response.body["Origin"]
        },
        owner_details: {
          id: response.body["Owner"]["Id"],
          name: response.body["Owner"]["Name"]
        },
        archived: response.body["Archived"],
        created_at: response.body["CreateTime"],
        closed_at: response.body["CloseTime"]
      }
    end

    # Get headlines for a user or a meeting.
    #
    # @param user_id [Integer, nil] the ID of the user (defaults to initialized user_id)
    # @param meeting_id [Integer, nil] the ID of the meeting
    # @raise [ArgumentError] if both `user_id` and `meeting_id` are provided
    # @return [Array<Hash>] a list of headlines containing:
    #   - id
    #   - title
    #   - meeting_details
    #   - owner_details
    #   - archived
    #   - created_at
    #   - closed_at
    # @example
    #   client.headline.list
    #   #=> [
    #     {
    #       id: 1,
    #       title: "Headline Title",
    #       meeting_details: { id: 1, title: "Team Meeting" },
    #       owner_details: { id: 1, name: "John Doe" },
    #       archived: false,
    #       created_at: "2023-01-01",
    #       closed_at: nil
    #     }
    #   ]
    def list(user_id: nil, meeting_id: nil)
      raise ArgumentError, "Please provide either `user_id` or `meeting_id`, not both." if user_id && meeting_id

      if meeting_id
        response = @conn.get("/api/v1/l10/#{meeting_id}/headlines")
      else
        user_id ||= self.user_id
        response = @conn.get("/api/v1/headline/users/#{user_id}")
      end

      raise "Failed to list headlines" unless response.success?

      response.body.map do |headline|
        {
          id: headline["Id"],
          title: headline["Name"],
          meeting_details: {
            id: headline["OriginId"],
            title: headline["Origin"]
          },
          owner_details: {
            id: headline["Owner"]["Id"],
            name: headline["Owner"]["Name"]
          },
          archived: headline["Archived"],
          created_at: headline["CreateTime"],
          closed_at: headline["CloseTime"]
        }
      end
    end

    # Deletes a headline
    #
    # @param headline_id [Integer] the ID of the headline to delete
    # @return [Boolean] true if the deletion was successful
    def delete(headline_id)
      response = @conn.delete("/api/v1/headline/#{headline_id}")
      response.success?
    end
  end
end

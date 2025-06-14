# frozen_string_literal: true

RSpec.describe "User Operations" do
  before(:all) do
    @client = Bloomy::Client.new
  end

  context "when interacting with the users API" do
    it "returns the basic user details" do
      user_details = @client.user.details
      expect(user_details).to be_a(Hash)
      expect(user_details[:name]).to be_a(String)
      expect(user_details[:id]).to be_a(Integer)
      expect(user_details[:image_url]).to be_a(String)
      expect(user_details[:direct_reports]).to be_nil
      expect(user_details[:positions]).to be_nil
    end

    it "returns the user details with direct reports" do
      user_details = @client.user.details(direct_reports: true)
      expect(user_details).to be_a(Hash)
      expect(user_details[:name]).to be_a(String)
      expect(user_details[:id]).to be_a(Integer)
      expect(user_details[:image_url]).to be_a(String)
      expect(user_details[:direct_reports]).to be_an(Array)
    end

    it "returns the user details with positions" do
      user_details = @client.user.details(positions: true)
      expect(user_details).to be_a(Hash)
      expect(user_details[:name]).to be_a(String)
      expect(user_details[:id]).to be_a(Integer)
      expect(user_details[:image_url]).to be_a(String)
      expect(user_details[:positions]).to be_an(Array)
    end

    it "returns the direct reports of the user" do
      direct_reports = @client.user.direct_reports
      expect(direct_reports).to all(be_a(Hash))
      direct_reports.each do |report|
        expect(report[:name]).to be_a(String)
        expect(report[:id]).to be_a(Integer)
        expect(report[:image_url]).to be_a(String)
      end
    end

    it "returns the positions of the user" do
      positions = @client.user.positions
      expect(positions).to all(be_a(Hash))
      positions.each do |position|
        expect(position[:id]).to be_a(Integer)
      end
    end

    it "returns the users that match the search term" do
      users = @client.user.search("fran")
      expect(users).to all(be_a(Hash))
      users.each do |user|
        expect(user[:id]).to be_a(Integer)
        expect(user[:name]).to be_a(String)
        expect(user[:description]).to be_a(String)
        expect(user[:email]).to be_a(String)
        expect(user[:organization_id]).to be_a(Integer)
        expect(user[:image_url]).to be_a(String)
      end
    end
  end
end

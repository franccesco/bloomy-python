# frozen_string_literal: true

RSpec.describe "Headline Operations" do
  # Set up a test meeting and tear it down
  before(:all) do
    @client = Bloomy::Client.new
    @meeting_id = @client.meeting.create("Test Meeting")[:meeting_id]
  end

  after(:all) do
    @client.meeting.delete(@meeting_id)
  end

  # Create a headline before each test
  before(:each) do
    @headline_id = @client.headline.create(meeting_id: @meeting_id, title: "Test Headline", notes: "Note!")[:id]
  end

  context "when managing headlines" do
    it "creates a new headline" do
      expect(@headline_id).not_to be_nil
    end

    it "updates a headline" do
      status = @client.headline.update(headline_id: @headline_id, title: "Updated Headline")
      expect(status).to be true
    end

    it "gets headline details" do
      headline = @client.headline.details(@headline_id)

      expect(headline[:title]).to eq("Test Headline")
      expect(headline[:meeting_details][:id]).to eq(@meeting_id)
      expect(headline[:meeting_details][:title]).to eq("Test Meeting")
      expect(headline[:notes_url]).not_to be_nil
    end

    it "gets user headlines" do
      headlines = @client.headline.list

      expect(headlines).not_to be_empty
      expect(headlines.first).to be_a(Hash)
    end

    it "gets meeting headlines" do
      headlines = @client.headline.list(meeting_id: @meeting_id)

      expect(headlines).not_to be_empty
      expect(headlines.first).to be_a(Hash)
    end

    it "deletes a headline" do
      status = @client.headline.delete(@headline_id)

      expect(status).to be true
    end
  end
end

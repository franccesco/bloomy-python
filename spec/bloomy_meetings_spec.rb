# frozen_string_literal: true

RSpec.describe "Meeting Operations" do
  # Set up a test meeting and tear it down
  before(:all) do
    @client = Bloomy::Client.new
    @meeting_id = @client.meeting.create("Test Meeting", add_self: true)[:meeting_id]
  end

  after(:all) do
    @client.meeting.delete(@meeting_id)
  end
  context "when interacting with meetings API" do
    it "returns a list of meetings" do
      meetings = @client.meeting.list
      expect(meetings).to all(be_a(Hash))
      expect(meetings.first).to include(
        id: be_kind_of(Integer),
        title: be_kind_of(String)
      )
    end

    it "returns a list of meeting attendees" do
      attendees = @client.meeting.attendees(@meeting_id)
      expect(attendees).to all(be_a(Hash))
      expect(attendees.first).to include(
        id: be_kind_of(Integer),
        name: be_kind_of(String)
      )
    end

    it "returns a list of meeting issues" do
      issues = @client.meeting.issues(@meeting_id)
      expect(issues).to all(include(:id, :title, :created_at, :completed_at, :notes_url, :user_id, :user_name))
    end

    it "returns a list of meeting todos" do
      todos = @client.meeting.todos(@meeting_id)
      expect(todos).to all(include(:id, :title, :due_date, :notes_url, :completed_at, :user_id, :user_name))
    end

    it "returns a list of meeting metrics" do
      metrics = @client.meeting.metrics(@meeting_id)
      expect(metrics).to all(be_a(Hash))

      # Skip detailed attribute checking if no metrics exist
      if metrics.any?
        expect(metrics.first).to include(
          id: be_kind_of(Integer),
          title: be_kind_of(String),
          target: be_kind_of(Numeric),
          operator: be_kind_of(String),
          format: be_kind_of(String),
          user_id: be_kind_of(Integer),
          user_name: be_kind_of(String),
          admin_id: be_kind_of(Integer),
          admin_name: be_kind_of(String)
        )
      end
    end

    it "returns meeting details" do
      details = @client.meeting.details(@meeting_id)
      expect(details).to be_a(Hash)
      expect(details).to include(
        id: be_kind_of(Integer),
        title: be_kind_of(String)
      )
      expect(details[:attendees]).to all(be_a(Hash))
      expect(details[:issues]).to all(be_a(Hash))
      expect(details[:todos]).to all(be_a(Hash))
      expect(details[:metrics]).to all(be_a(Hash))
    end
  end
end

# frozen_string_literal: true

require "date"

RSpec.describe "Todo Operations" do
  before(:all) do
    @client = Bloomy::Client.new
    @meeting_id = @client.meeting.create("Test Meeting")[:meeting_id]
    @due_date_7days = (Date.today + 7).to_s
    @todo = @client.todo.create(title: "New Todo", meeting_id: @meeting_id, notes: "Note!")
  end

  after(:all) do
    @client.meeting.delete(@meeting_id)
  end

  context "when interacting with todos API" do
    it "creates a todo" do
      expect(@todo).to be_a(Hash)
      expect(@todo[:id]).to be_a(Integer)
      expect(@todo[:title]).to be_a(String)
      expect(@todo[:notes_url]).to be_a(String)
    end

    it "updates a todo" do
      updated_todo = @client.todo.update(todo_id: @todo[:id], title: "Updated Todo")
      expect(updated_todo).to be_a(Hash)
      expect(updated_todo[:id]).to eq(@todo[:id])
      expect(updated_todo[:title]).to eq("Updated Todo")
    end

    it "gets todo details" do
      todo_details = @client.todo.details(@todo[:id])
      expect(todo_details).to be_a(Hash)
      expect(todo_details[:id]).to eq(@todo[:id])
      expect(todo_details[:title]).to eq("Updated Todo")
      expect(todo_details[:due_date]).to be_a(String)
      expect(todo_details[:created_at]).to be_a(String)
      expect(todo_details[:completed_at]).to be_nil
      expect(todo_details[:status]).to eq("Incomplete")
    end

    it "lists the current user todos" do
      todos = @client.todo.list
      expect(todos).to all(be_a(Hash))

      sample_todo = todos.first
      expect(sample_todo[:id]).to be_a(Integer)
      expect(sample_todo[:title]).to be_a(String)
      expect(sample_todo[:due_date]).to be_a(String)
      expect(sample_todo[:created_at]).to be_a(String)
      expect(sample_todo[:status]).to match(/Complete|Incomplete/)
      expect(sample_todo[:notes_url]).to be_a(String)
    end

    it "lists the meeting todos" do
      todos = @client.todo.list(meeting_id: @meeting_id)
      expect(todos).to all(be_a(Hash))
      expect(todos).to_not be_empty
    end

    it "completes a todo" do
      completed_todo = @client.todo.complete(@todo[:id])
      expect(completed_todo).to be true
    end
  end
end

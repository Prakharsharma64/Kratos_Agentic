import React from 'react'
import type { CouncilUpdate } from '../types'
import './CouncilVisualization.css'

interface CouncilVisualizationProps {
  council: CouncilUpdate
}

export default function CouncilVisualization({ council }: CouncilVisualizationProps) {
  return (
    <div className="council-visualization">
      <h3>Council Reasoning</h3>
      <div className="council-stage">Stage: {council.stage}</div>
      
      {council.dissent && (
        <div className="council-dissent">⚠️ Disagreement detected</div>
      )}

      <div className="council-members">
        {council.members.map((member) => (
          <div
            key={member.id}
            className={`council-member ${member.status} ${council.dissent ? 'has-dissent' : ''}`}
          >
            <div className="member-header">
              <span className="member-id">Member {member.id + 1}</span>
              <span className="member-score">Score: {member.score.toFixed(2)}</span>
            </div>
            <div className="member-opinion">{member.opinion}</div>
            <div className="member-status">{member.status}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

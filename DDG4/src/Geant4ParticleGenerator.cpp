//==========================================================================
//  AIDA Detector description implementation 
//--------------------------------------------------------------------------
// Copyright (C) Organisation europeenne pour la Recherche nucleaire (CERN)
// All rights reserved.
//
// For the licensing terms see $DD4hepINSTALL/LICENSE.
// For the list of contributors see $DD4hepINSTALL/doc/CREDITS.
//
// Author     : M.Frank
//
//==========================================================================

// Framework include files
#include "DD4hep/Printout.h"
#include "DD4hep/InstanceCount.h"
#include "DDG4/Geant4Context.h"
#include "DDG4/Geant4Primary.h"
#include "DDG4/Geant4ParticleGenerator.h"
#include "CLHEP/Units/SystemOfUnits.h"

// Geant4 include files
#include "G4ParticleTable.hh"
#include "G4ParticleDefinition.hh"

// C/C++ include files
#include <stdexcept>
#include <cmath>

using namespace std;
using namespace dd4hep::sim;

/// Standard constructor
Geant4ParticleGenerator::Geant4ParticleGenerator(Geant4Context* ctxt, const string& nam)
  : Geant4GeneratorAction(ctxt, nam), m_direction(0,1,0), m_position(0,0,0), m_particle(0)
{
  InstanceCount::increment(this);
  m_needsControl = true;
  declareProperty("Particle",      m_particleName = "e-");
  declareProperty("Energy",        m_energy = 50 * CLHEP::MeV);
  declareProperty("Multiplicity",  m_multiplicity = 1);
  declareProperty("Mask",          m_mask = 0);
  declareProperty("Position",      m_position = ROOT::Math::XYZVector(0.,0.,0.));
  declareProperty("Direction",     m_direction = ROOT::Math::XYZVector(1.,1.,1.));
}

/// Default destructor
Geant4ParticleGenerator::~Geant4ParticleGenerator() {
  InstanceCount::decrement(this);
}

/// Particle modification. Caller presets defaults to: ( direction = m_direction, momentum = m_energy)
void Geant4ParticleGenerator::getParticleDirection(int , ROOT::Math::XYZVector& , double& ) const   {
}

/// Particle modification. Caller presets defaults to: (multiplicity=m_multiplicity)
void Geant4ParticleGenerator::getParticleMultiplicity(int& ) const   {
}

/// Particle modification. Caller presets defaults to: (multiplicity=m_multiplicity)
void Geant4ParticleGenerator::getVertexPosition(ROOT::Math::XYZVector& ) const   {
}

/// Print single particle interaction identified by its mask
void Geant4ParticleGenerator::printInteraction(int mask)  const  {
  Geant4PrimaryEvent* prim = context()->event().extension<Geant4PrimaryEvent>();
  if ( !prim )   {
    warning("printInteraction: Bad primary event [NULL-Pointer].");
    return;
  }
  Geant4PrimaryInteraction* inter = prim->get(mask);
  if ( !inter )   {
    warning("printInteraction: Bad interaction identifier 0x%08X [Unknown Mask].",mask);
    return;
  }
  printInteraction(inter);
}

/// Print single particle interaction identified by its reference
void Geant4ParticleGenerator::printInteraction(Geant4PrimaryInteraction* inter)  const  {
  int count = 0;
  if ( !inter )   {
    warning("printInteraction: Invalid interaction pointer [NULL-Pointer].");
    return;
  }
  for(const auto& iv : inter->vertices )   {
    for( Geant4Vertex* v : iv.second ){
      print("+-> Interaction [%d] %.3f GeV %s pos:(%.3f %.3f %.3f)[mm]",
            count, m_energy/CLHEP::GeV, m_particleName.c_str(),
            v->x/CLHEP::mm, v->y/CLHEP::mm, v->z/CLHEP::mm);
      ++count;
      for ( int i : v->out )  {
        Geant4ParticleHandle p = inter->particles[i];
        p.dumpWithVertex(outputLevel(),name(),"  +->");
      }
    }
  }
}

/// Callback to generate primary particles
void Geant4ParticleGenerator::operator()(G4Event*) {
  typedef Geant4Particle Particle;

  if (0 == m_particle || m_particle->GetParticleName() != m_particleName.c_str()) {
    G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    m_particle = particleTable->FindParticle(m_particleName);
    if (0 == m_particle) {
      throw runtime_error("Geant4ParticleGenerator: Bad particle type:"+m_particleName+"!");
    }
  }
  Geant4Event& evt = context()->event();
  Geant4PrimaryEvent* prim = evt.extension<Geant4PrimaryEvent>();
  Geant4PrimaryInteraction* inter = new Geant4PrimaryInteraction();
  prim->add(m_mask, inter);

  Geant4Vertex* vtx = new Geant4Vertex();
  int multiplicity = m_multiplicity;
  ROOT::Math::XYZVector unit_direction, position = m_position;
  getVertexPosition(position);
  getParticleMultiplicity(multiplicity);
  vtx->mask = m_mask;
  vtx->x = position.X();
  vtx->y = position.Y();
  vtx->z = position.Z();
  inter->vertices[m_mask].emplace_back( vtx );
  for(int i=0; i<m_multiplicity; ++i)   {
    double momentum = m_energy;
    ROOT::Math::XYZVector direction = m_direction;
    Particle* p = new Particle();
    getParticleDirection(i, direction, momentum);
    unit_direction  = direction.unit();
    p->id           = inter->nextPID();
    p->status      |= G4PARTICLE_GEN_STABLE;
    p->mask         = m_mask;
    p->pdgID        = m_particle->GetPDGEncoding();

    p->psx          = unit_direction.X()*momentum;
    p->psy          = unit_direction.Y()*momentum;
    p->psz          = unit_direction.Z()*momentum;
    p->mass         = m_particle->GetPDGMass();
    p->charge       = m_particle->GetPDGCharge();
    p->spin[0]      = 0;
    p->spin[1]      = 0;
    p->spin[2]      = 0;
    p->colorFlow[0] = 0;
    p->colorFlow[1] = 0;
    p->vsx        = vtx->x;
    p->vsy        = vtx->y;
    p->vsz        = vtx->z;
    //fg: do not set the endpoint to the start point of the particle
    // p->vex        = vtx->x;
    // p->vey        = vtx->y;
    // p->vez        = vtx->z;
    inter->particles.emplace(p->id,p);
    vtx->out.insert(p->id);
    printout(INFO,name(),"Particle [%d] %-12s Mom:%.3f GeV vertex:(%6.3f %6.3f %6.3f)[mm] direction:(%6.3f %6.3f %6.3f)",
             p->id, m_particleName.c_str(), momentum/CLHEP::GeV,
	     vtx->x/CLHEP::mm, vtx->y/CLHEP::mm, vtx->z/CLHEP::mm,
	     direction.X(), direction.Y(), direction.Z());

  }
}

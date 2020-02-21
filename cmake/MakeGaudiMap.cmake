IF($ENV{VERBOSE})
  MESSAGE(" *** Gaudi listcomponents: Generate map for ${libname} ..." )
  MESSAGE(" *** MakeGaudiMap.cmake run command : ${DD4HEP_LISTCOMPONENTS_CMD} -o ${rootmapfile} ${libname}
                    WORKING_DIRECTORY ${LIBRARY_LOCATION} "
    )
ENDIF()
  GET_FILENAME_COMPONENT(GAUDI_LISTCOMP_INSTALL ${DD4HEP_LISTCOMPONENTS_CMD} DIRECTORY)
  if(APPLE)
    SET ( ENV{DYLD_LIBRARY_PATH} ${LIBRARY_LOCATION}:${DD4HEP_LIBRARY_LOCATION}:$ENV{DYLD_LIBRARY_PATH}:$ENV{DD4HEP_LIBRARY_PATH} )
  else()
    SET ( ENV{LD_LIBRARY_PATH} ${LIBRARY_LOCATION}:${DD4HEP_LIBRARY_LOCATION}:$ENV{LD_LIBRARY_PATH} )
  endif()
  # EXECUTE_PROCESS( COMMAND echo LD_LIBRARY_PATH = $ENV{LD_LIBRARY_PATH} )
  EXECUTE_PROCESS( COMMAND 
    ${DD4HEP_LISTCOMPONENTS_CMD} -o ${rootmapfile} ${libname}
    WORKING_DIRECTORY ${LIBRARY_LOCATION}
    )
